"""
LiquidacionPatchVisitasService — recalculo PATCH para motor Visitas (Inspección de Obra).

ALCANCE: Solo servicio — sin controller, sin exposición API. El siguiente paquete integra el endpoint.

Aplica a tipo Visitas: Inspección de Obra.

Reglas clave:
- Resuelve IGV/UIT por LiquidacionGeneral.fecha_registro.date()
  vía LiquidacionHistoricoCoreService (NO vigentes actuales).
- Tarifa resuelta vía TarifaLiquidacionBase vigente en fecha_registro.
- Si patch.tarifa_visitas_id es proporcionado: valida que exista y su base
  estaba vigente en fecha_registro.
- Si patch.tarifa_visitas_id es None: preserva el TarifaPorCategoriaVisitas almacenado actualmente.
- Si patch.categoria es proporcionado sin patch.tarifa_visitas_id:
  busca el TarifaPorCategoriaVisitas para esa categoria + base histórica.
  Lanza error si no se encuentra tarifa coincidente para la fecha histórica.
- Aritmética pura vía el MOTOR ÚNICO de Visitas
  (`calcular_cotizacion_visitas_estrategia`): el contexto llega RESUELTO
  (tarifa, UIT, IGV histórico y crédito) y el motor devuelve la proyección
  autoritativa. La rama NORMAL conserva la aritmética vigente sin cuantizar
  (byte-compatible); la rama CONTINUAR cuantiza y devuelve la diferencia.
- Actualización en lugar de una sola fila de LiquidacionPorCategoriaVisitas.
- LiquidacionGeneral.sub_total y .total actualizados atómicamente.
- CONTINUIDAD: si la IO tiene fila de continuidad, `sub_total`/`total` son la
  DIFERENCIA a cobrar, no el valor completo. El recálculo vuelve a calcular
  `monto_acumulado`/`total_acumulado` y reaplica la diferencia; el crédito de
  la previa queda congelado. La diferencia la calcula el MOTOR y NO se
  recalcula al aplicarla: lo persistido es idéntico a lo cotizado.
- SEPARACIÓN CALCULO/TOTALES: `recalcular_visitas()` reprecia y persiste el
  motor de visitas (y devuelve los montos derivados) SIN escribir
  `sub_total`/`total`; la decisión de qué se cobra la toma el orquestador con
  `aplicar_totales*`. Así el encendido/apagado de la continuidad puede
  orquestarse ALREDEDOR del recálculo y no como un ajuste posterior
  (Explorer §5.2).
- igv_snapshot y uit_snapshot actualizados (Visitas usa IGV en el total).
- Preserva campos del patch omitidos (cantidad_visitas, categoria, tarifa_visitas_id).
- Lanza BusinessError claro si falta IGV/UIT/tarifa histórico o tarifa no encontrada.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
    NoIGVVigenteError,
    NoUITVigenteError,
    NoTarifaVigenteError,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_continuidad_visitas_core_service import (
    LiquidacionContinuidadVisitasCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    ContinuidadCreditoVisitas,
)
from modules.liquidaciones.domain.constants import ModoCotizacionVisitas
from core.exceptions import BusinessError


class LiquidacionVisitasNoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no LiquidacionPorCategoriaVisitas."""

    def __init__(self, liquidacion_general_id: str):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro "
            f"LiquidacionPorCategoriaVisitas. No se puede recalcular."
        )


class LiquidacionVisitasSinTarifaError(BusinessError):
    """Raised when the Visitas record has no applied tariff (manual/legacy records)."""

    def __init__(self, liquidacion_general_id: str):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene tarifa de visitas "
            f"aplicada (registro manual/legacy). No se puede recalcular."
        )


class NoTarifaVisitasError(BusinessError):
    """Raised when no TarifaPorCategoriaVisitas exists for the given categoria and fecha."""

    def __init__(self, categoria: str, fecha: date):
        super().__init__(
            f"No existe tarifa de visitas para la categoria '{categoria}' "
            f"vigente en la fecha {fecha}. No se puede recalcular."
        )


@dataclass
class PatchVisitasInput:
    """
    Optional patch inputs for Visitas recalculation.

    If a field is None, the current stored value is preserved.
    """
    cantidad_visitas: Optional[int] = None
    categoria: Optional[str] = None
    tarifa_visitas_id: Optional[str] = None


@dataclass
class RecalculoVisitasResultado:
    """
    Montos derivados del recálculo de B — SIN decidir todavía qué se cobra.

    `recalcular_visitas()` produce este resultado y NO escribe
    `LiquidacionGeneral.sub_total` / `total`: esa decisión depende de si la IO
    tiene (o tendrá) fila de continuidad, y por eso la toma el orquestador
    mediante `aplicar_totales*` (Explorer §5.2).

    - `subtotal` / `total`: cotización completa del trabajo (sin continuidad).
    - `monto_acumulado` / `total_acumulado`: valor completo del trabajo con la
      precisión monetaria del proyecto (`monto_acumulado` es el neto;
      `total_acumulado` su contraparte bruta). Es lo que se congela en la fila
      de continuidad y lo que sirve de base al RH.
    - `diferencia_neto` / `diferencia_bruto`: la DIFERENCIA a cobrar que
      calculó el MOTOR en modo CONTINUAR (`None` en modo NORMAL, donde no hay
      continuidad). NO se recalcula en `aplicar_totales*`: lo que se persiste
      es EXACTAMENTE lo que devolvió la cotización.
    """

    liquidacion_visitas: LiquidacionPorCategoriaVisitas
    subtotal: Decimal
    total: Decimal
    monto_acumulado: Decimal
    total_acumulado: Decimal
    igv: IGV
    uit: UIT
    diferencia_neto: Optional[Decimal] = None
    diferencia_bruto: Optional[Decimal] = None


class LiquidacionPatchVisitasService:
    """
    Recalculation service for Visitas-type liquidaciones (Inspección de Obra) via PATCH.

    Sync core service — caller provides transaction.atomic() if needed.

    Usage:
        service = LiquidacionPatchVisitasService()
        with transaction.atomic():
            service.recalcular(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico_service = LiquidacionHistoricoCoreService()
        self._visitas_core = LiquidacionPorCategoriaVisitasCoreService()

    def recalcular(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchVisitasInput,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Recalculate a Visitas liquidacion with optional patch inputs.

        All DB writes happen inside this method (caller wraps in transaction.atomic).

        Es el camino SIN operación de continuidad: reprecia B y reaplica la
        diferencia si la IO ya tiene fila de continuidad (crédito congelado) o
        el valor completo si no la tiene.

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — cantidad_visitas, categoria, and/or tarifa_visitas_id.

        Returns:
            Updated LiquidacionPorCategoriaVisitas instance (caller should refresh).

        Raises:
            LiquidacionVisitasNoEncontradaError: No Visitas record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base vigente at fecha_registro
                                  (when explicit tarifa_visitas_id provided but its
                                  base is not vigente at fecha_registro).
            NoTarifaVisitasError: categoria changed but no matching tariff for that
                                  categoria at fecha_registro.
        """
        resultado = self.recalcular_visitas(liquidacion_general, patch)
        self.aplicar_totales(liquidacion_general, resultado)
        return resultado.liquidacion_visitas

    def recalcular_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchVisitasInput,
        *,
        continuidad_credito: Optional[ContinuidadCreditoVisitas] = None,
    ) -> RecalculoVisitasResultado:
        """
        Recalcula y PERSISTE el motor de visitas de B (cantidad, categoría, tarifa).

        NO escribe `LiquidacionGeneral.sub_total` / `total`: decidir si la IO
        cobra el valor completo o la DIFERENCIA depende del estado de la
        continuidad, y esa decisión la toma el orquestador (Explorer §5.2).
        Los snapshots financieros (`igv_snapshot`, `uit_snapshot`, `igv_id`,
        `uit_id`) quedan cargados en el objeto en memoria; los persiste el
        `aplicar_totales*` que se invoque a continuación.

        La aritmética la hace el MOTOR ÚNICO (`calcular_cotizacion_visitas_estrategia`),
        con el contexto YA RESUELTO (tarifa, UIT, IGV histórico y crédito): lo
        que se persiste es EXACTAMENTE lo que devolvió la cotización (C-7).

        El MODO del motor:
        - `continuidad_credito` explícito → CONTINUAR (operación de continuidad:
          el crédito lo resolvió el orquestador).
        - sin crédito explícito pero con fila de continuidad vigente →
          CONTINUAR con el crédito CONGELADO de esa fila (comportamiento
          vigente: reprecia B y reaplica la diferencia).
        - sin fila de continuidad → NORMAL (la aritmética vigente, sin
          cuantizar: byte-compatible).

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — cantidad_visitas, categoria, and/or tarifa_visitas_id.
            continuidad_credito: Crédito de la continuidad que se entrega al
                motor (bruto declarado / par neto-bruto). `None` = resolverlo
                desde la fila de continuidad vigente.

        Returns:
            RecalculoVisitasResultado con los montos derivados del recálculo.
        """
        # ── 1. Get Visitas record via reverse FK accessor ────────────────────────
        # LiquidacionPorCategoriaVisitas has ForeignKey to LiquidacionGeneral with
        # related_name="liquidacion_visitas" — use .get() to fetch the single object.
        try:
            liq_visitas = liquidacion_general.liquidacion_visitas.get()
        except ObjectDoesNotExist:
            raise LiquidacionVisitasNoEncontradaError(str(liquidacion_general.id))

        # ── 2. Resolve historical date and tipo ───────────────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        # ── 3. Resolve historical IGV and UIT ────────────────────────────────────
        igv = self._historico_service.get_igv_por_fecha(fecha)
        uit = self._historico_service.get_uit_por_fecha(fecha)

        # ── 4. Determine cantidad_visitas ───────────────────────────────────────
        cantidad_visitas = patch.cantidad_visitas
        if cantidad_visitas is None:
            cantidad_visitas = liq_visitas.cantidad_visitas

        # ── 5. Determine tarifa_aplicada (most complex rule) ───────────────────
        if patch.tarifa_visitas_id is not None:
            # Explicit tariff ID provided — validate it exists and its base
            # was vigente at fecha_registro (historical accuracy).
            tarifa = self._get_tarifa_validated(patch.tarifa_visitas_id, tipo_liq, fecha)
            # Use the tariff's categoria_visitas as the categoria.
            categoria = tarifa.categoria_visitas
        elif patch.categoria is not None:
            # Only categoria changed — look up the TarifaPorCategoriaVisitas
            # for this categoria + historical base. Raises NoTarifaVisitasError
            # if no matching tariff found for the historical date.
            categoria = patch.categoria
            tarifa = self._get_tarifa_by_categoria(categoria, tipo_liq, fecha)
        else:
            # Neither tariff nor categoria provided — preserve current tariff.
            tarifa = liq_visitas.tarifa_aplicada
            if tarifa is None:
                # Registro manual/legacy (CATEGORIA=0): no hay tarifa que
                # repreciar. Se rechaza explícitamente en vez de reventar con
                # un AttributeError.
                raise LiquidacionVisitasSinTarifaError(str(liquidacion_general.id))
            categoria = liq_visitas.categoria

        # ── 6. MOTOR ÚNICO: contexto resuelto → proyección autoritativa ────────
        credito = continuidad_credito
        if credito is None:
            # Sin operación de continuidad explícita: si la IO YA tiene fila de
            # continuidad, su crédito queda CONGELADO (comportamiento vigente).
            fila_continuidad = (
                LiquidacionContinuidadVisitasCoreService.get_continuidad(liq_visitas)
            )
            if fila_continuidad is not None:
                credito = ContinuidadCreditoVisitas(
                    credito_neto=fila_continuidad.subtotal_credito,
                    credito_bruto=fila_continuidad.total_credito,
                )

        modo = (
            ModoCotizacionVisitas.CONTINUAR
            if credito is not None
            else ModoCotizacionVisitas.NORMAL
        )
        contexto = self._visitas_core.construir_contexto_visitas(
            modo=modo,
            cantidad_visitas=cantidad_visitas,
            porcentaje_uit=Decimal(str(tarifa.porcentaje_uit)),
            uit_valor=Decimal(str(uit.valor)),
            igv_porcentaje=Decimal(str(igv.valor)),
            categoria=categoria,
            tarifa_id=str(tarifa.id),
            total_pagado_previa=credito.total_pagado_previa if credito else None,
            credito_neto=credito.credito_neto if credito else None,
            credito_bruto=credito.credito_bruto if credito else None,
            uit_id=str(uit.id),
            igv_id=str(igv.id),
        )
        estrategia = self._visitas_core.calcular_cotizacion_visitas_estrategia(
            contexto
        )

        # ── 7. Update Visitas row in-place ──────────────────────────────────────
        liq_visitas.cantidad_visitas = cantidad_visitas
        liq_visitas.categoria = categoria
        liq_visitas.porcentaje_uit = Decimal(str(tarifa.porcentaje_uit))
        liq_visitas.tarifa_aplicada = tarifa
        liq_visitas.save()

        # ── 8. Derive the accumulated amounts (value of the WHOLE job) ─────────
        # `monto_acumulado` / `total_acumulado` son el valor completo del
        # trabajo de B con precisión monetaria: es lo que se congela en la fila
        # de continuidad y lo que sirve de base al RH.
        #
        # En CONTINUAR los toma del propio MOTOR (su bloque `continuidad`); en
        # NORMAL se derivan con la primitiva de precisión monetaria — el valor
        # completo NO se mueve (CP-11/R10: `monto_acumulado` es la base RH).
        diferencia_neto = None
        diferencia_bruto = None
        if estrategia.continuidad is not None:
            monto_acumulado = estrategia.continuidad.valor_completo_neto
            total_acumulado = estrategia.continuidad.valor_completo_bruto
            diferencia_neto = estrategia.continuidad.diferencia_neto
            diferencia_bruto = estrategia.continuidad.diferencia_bruto
        else:
            monto_acumulado, total_acumulado = (
                LiquidacionContinuidadVisitasCoreService.calcular_montos_acumulados(
                    monto_neto_visitas=estrategia.subtotal,
                    igv_valor=igv.valor,
                )
            )

        # ── 9. Load the financial snapshots on the header (in memory) ───────────
        liquidacion_general.igv_snapshot = igv.valor
        liquidacion_general.uit_snapshot = Decimal(str(uit.valor))
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit

        return RecalculoVisitasResultado(
            liquidacion_visitas=liq_visitas,
            subtotal=Decimal(str(estrategia.subtotal)),
            total=Decimal(str(estrategia.total)),
            monto_acumulado=monto_acumulado,
            total_acumulado=total_acumulado,
            igv=igv,
            uit=uit,
            diferencia_neto=diferencia_neto,
            diferencia_bruto=diferencia_bruto,
        )

    def aplicar_totales(
        self,
        liquidacion_general: LiquidacionGeneral,
        resultado: RecalculoVisitasResultado,
    ) -> None:
        """
        Aplica `sub_total` / `total` según el estado PERSISTIDO de la continuidad.

        - CON fila de continuidad: `sub_total` / `total` son la DIFERENCIA a
          cobrar. La fila se actualiza con el nuevo valor completo del trabajo
          y el CRÉDITO queda CONGELADO (pertenece a la liquidación previa y no
          depende de B).
        - SIN fila de continuidad: `sub_total` / `total` son el VALOR COMPLETO
          del trabajo (comportamiento vigente, bit a bit).

        La DIFERENCIA la calculó el MOTOR (`resultado.diferencia_neto` /
        `resultado.diferencia_bruto`): aquí NO se recalcula, se aplica. Eso es
        lo que garantiza que lo persistido sea idéntico a lo cotizado.

        `LiquidacionContinuidadVisitasCoreService` se usa por su API
        estática: instanciarlo aquí violaría el contrato Django P4
        ("nunca instanciar servicios a mano dentro de otros servicios").
        """
        continuidad = LiquidacionContinuidadVisitasCoreService.get_continuidad(
            resultado.liquidacion_visitas
        )
        if continuidad is None:
            liquidacion_general.sub_total = resultado.subtotal
            liquidacion_general.total = resultado.total
        else:
            LiquidacionContinuidadVisitasCoreService.recalcular_continuidad(
                continuidad,
                monto_acumulado=resultado.monto_acumulado,
                total_acumulado=resultado.total_acumulado,
            )
            sub_total, total = self._diferencia_del_motor(
                resultado,
                subtotal_credito=continuidad.subtotal_credito,
                total_credito=continuidad.total_credito,
            )
            liquidacion_general.sub_total = sub_total
            liquidacion_general.total = total

        liquidacion_general.save()

    def aplicar_totales_valor_completo(
        self,
        liquidacion_general: LiquidacionGeneral,
        resultado: RecalculoVisitasResultado,
    ) -> None:
        """
        Fuerza `sub_total` / `total` = VALOR COMPLETO del trabajo de B.

        Es el estado de una IO SIN continuidad: lo usa el modo `desactivar`
        (que elimina la fila y restaura los montos normales de B).
        """
        liquidacion_general.sub_total = resultado.subtotal
        liquidacion_general.total = resultado.total
        liquidacion_general.save()

    def aplicar_totales_diferencia(
        self,
        liquidacion_general: LiquidacionGeneral,
        resultado: RecalculoVisitasResultado,
        *,
        subtotal_credito: Optional[Decimal] = None,
        total_credito: Optional[Decimal] = None,
    ) -> None:
        """
        Fuerza `sub_total` / `total` = la DIFERENCIA que calculó el MOTOR.

        Es el estado de una IO CON continuidad: lo usan los modos `activar`
        (recién creada) y `mantener` (crédito actualizado). El crédito es
        explícito porque en `mantener` todavía no está escrito en la fila.

        La diferencia YA NO se recalcula aquí: viene del resultado del MOTOR
        (`diferencia_neto` / `diferencia_bruto`), de modo que lo que se
        persiste es EXACTAMENTE lo que devolvió la cotización (paridad al
        céntavo).

        `subtotal_credito` / `total_credito` quedan como REPLIEGO defensivo
        para un resultado sin diferencias del motor (no debería ocurrir: el
        motor las devuelve siempre en modo CONTINUAR).
        """
        sub_total, total = self._diferencia_del_motor(
            resultado,
            subtotal_credito=subtotal_credito,
            total_credito=total_credito,
        )
        liquidacion_general.sub_total = sub_total
        liquidacion_general.total = total
        liquidacion_general.save()

    @staticmethod
    def _diferencia_del_motor(
        resultado: RecalculoVisitasResultado,
        *,
        subtotal_credito: Optional[Decimal] = None,
        total_credito: Optional[Decimal] = None,
    ) -> tuple[Decimal, Decimal]:
        """
        Devuelve la DIFERENCIA a cobrar que calculó el MOTOR.

        Es la fuente de verdad de `sub_total` / `total` en la IO con
        continuidad: la misma cifra que devolvió la cotización. El repliego
        con la primitiva de diferencia solo cubre el caso defensivo de un
        resultado sin diferencias del motor.
        """
        if resultado.diferencia_neto is not None and resultado.diferencia_bruto is not None:
            return resultado.diferencia_neto, resultado.diferencia_bruto

        if subtotal_credito is None or total_credito is None:
            raise BusinessError(
                "El recálculo de visitas no devolvió la diferencia de la "
                "continuidad.",
                code="IO_DIFERENCIA_CONTINUIDAD_AUSENTE",
            )

        return LiquidacionContinuidadVisitasCoreService.calcular_diferencia(
            monto_acumulado=resultado.monto_acumulado,
            total_acumulado=resultado.total_acumulado,
            subtotal_credito=subtotal_credito,
            total_credito=total_credito,
        )

    def _get_tarifa_validated(
        self,
        tarifa_visitas_id: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """
        Get a TarifaPorCategoriaVisitas by ID and validate it was vigente at fecha.

        Raises:
            NoTarifaVigenteError: if the tariff's TarifaLiquidacionBase is not
                                  vigente at fecha (historical accuracy violation).
            NoTarifaVisitasError: if the tariff ID does not exist.
        """
        try:
            tarifa = TarifaPorCategoriaVisitas.objects.select_related("tarifa_base").get(
                id=tarifa_visitas_id
            )
        except TarifaPorCategoriaVisitas.DoesNotExist:
            raise NoTarifaVisitasError(tarifa_visitas_id, fecha)

        # Validate the tariff's base was vigente at fecha_registro
        # Use TarifaLiquidacionBase.vigentes() (VigenciaModel) not the visitas model.
        vigente_base_ids = set(
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .values_list("id", flat=True)
        )
        if tarifa.tarifa_base_id not in vigente_base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        return tarifa

    def _get_tarifa_by_categoria(
        self,
        categoria: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """
        Get a TarifaPorCategoriaVisitas by categoria name and validate its base
        was vigente at fecha.

        Used when categoria is changed without an explicit tariff ID — we need
        to find the tariff that corresponds to the new categoria for the
        historical date.

        Raises:
            NoTarifaVisitasError: if no tariff exists for this categoria at fecha,
                                  or if the tariff's base was not vigente at fecha.
        """
        # Get all TarifaLiquidacionBase vigente at fecha for this tipo.
        base_ids = [
            tb.id for tb in
            self._historico_service.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        ]
        if not base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        # Find the TarifaPorCategoriaVisitas matching this categoria.
        tarifa = (
            TarifaPorCategoriaVisitas.objects
            .filter(tarifa_base_id__in=base_ids)
            .filter(categoria_visitas=categoria)
            .select_related("tarifa_base")
            .first()
        )
        if tarifa is None:
            raise NoTarifaVisitasError(categoria, fecha)

        return tarifa
