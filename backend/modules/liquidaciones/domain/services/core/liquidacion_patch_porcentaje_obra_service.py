"""
LiquidacionPatchPorcentajeObraService — recalculo PATCH para motor PO (Edificaciones, Taludes, Impacto Vial).

ALCANCE: Solo servicio — sin controller, sin exposición API. El siguiente paquete integra el endpoint.

Aplica a tipos PO: Edificaciones, Impacto Vial, Taludes.

Reglas clave:
- Resuelve IGV/UIT/tarifas/derecho por LiquidacionGeneral.fecha_registro.date()
  vía LiquidacionPatchHistoricoCoreService (NO vigentes actuales).
- Recalcula vía calcular_cotizacion_po existente (aritmética pura, sin lógica de fecha).
- Filas de detalle: eliminar + recrear atómicamente (UniqueConstraint
  (liquidacion_porcentaje, especialidad) impide upsert simple).
- Los detalles recreados persisten `importe_parcial` y `ajuste_redondeo` — los mismos
  campos que escribe el alta en create_liquidacion_porcentaje_obra. Sin ellos el
  consumidor RH/CODEMU (finanzas_core_service.get_importes_po_detalle) lee 0.00.
- Lock de fila (SELECT ... FOR UPDATE) sobre el LiquidacionGeneral al inicio del
  recálculo. El lock se toma dentro de la transacción que abre el llamador
  (orquestador/flujo); este servicio NUNCA abre la suya propia
  (django-app-architecture-contract.md §4.3).
- `modo_calculo=MANUAL` (edge) NO es recalculable por tarifa: se rechaza con
  ConflictError (409) en lugar de reventar con TypeError (500).
- Totales del PO padre + LiquidacionGeneral actualizados en la misma transacción.
- Si se omite un campo del patch, preserva el valor actual/detalles aplicados actuales.
- Lanza BusinessError claro si falta tarifa/derecho/IGV/UIT histórico.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction

from modules.liquidaciones.domain.constants import ModoCalculoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    CotizacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from core.exceptions import BusinessError, ConflictError


class LiquidacionNoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no LiquidacionPorcentajeObra."""

    def __init__(self, liquidacion_general_id):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro "
            f"LiquidacionPorcentajeObra. No se puede recalcular."
        )


class ModoCalculoManualNoEditableError(ConflictError):
    """
    Raised when a PATCH tries to recalculate a liquidacion created in MANUAL mode.

    A MANUAL (edge) liquidacion has no tarifa, no porcentaje and no derecho: its
    details were distributed from a manual subtotal. Recalculating it with the
    tariff engine is mathematically impossible (the engine would sum a NULL
    percentage) and semantically wrong (it would silently replace a manual
    amount with a tariff amount).

    Therefore the edit is rejected explicitly with 409 instead of failing with a
    TypeError (HTTP 500).
    """

    def __init__(self, liquidacion_general_id):
        super().__init__(
            message=(
                f"La liquidacion {liquidacion_general_id} fue creada en modo MANUAL "
                "y no admite recalculo por tarifa. No se puede editar."
            ),
            code="LIQUIDACION_MODO_MANUAL_NOT_EDITABLE",
        )


@dataclass
class TarifaPatchInput:
    """A single tariff + especialidad pair for PATCH recalculation."""
    tarifa_id: str
    especialidad_id: str


@dataclass
class PatchPorcentajeObraInput:
    """
    Optional patch inputs for PO recalculation.

    If a field is None, the current value is preserved.

    Module 5 — soporte de estrategias (SOLO Edificaciones):
    - `estrategia`: NORMAL_SELECCIONADAS | TARIFA_HABILITADAS_PARTICIPANTES |
      TOTAL_EXPLICITO. `None` = camino LEGACY (Taludes, Impacto Vial): se usa la
      fachada `calcular_cotizacion_po` y NO se toca la acumulación.
    - `total_explicito`: total final autoritativo (TOTAL_EXPLICITO).
    - `count_habilitadas`: H ya resuelto por el llamador (snapshot/catálogo).
      NUNCA se deduce de los participantes.
    """
    valor_declarado: Optional[Decimal] = None
    tarifas: Optional[list[TarifaPatchInput]] = None
    tipo_tramite: Optional[str] = None
    estrategia: Optional[str] = None
    total_explicito: Optional[Decimal] = None
    count_habilitadas: Optional[int] = None


class LiquidacionPatchPorcentajeObraService:
    """
    Recalculation service for PO-type liquidaciones via PATCH.

    Sync core service — caller provides transaction.atomic() if needed.

    Usage:
        service = LiquidacionPatchPorcentajeObraService()
        with transaction.atomic():
            service.recalcular(liquidacion_general_id, patch_input)
    """

    def __init__(self) -> None:
        self._historico_service = LiquidacionPatchHistoricoCoreService()
        self._po_core = LiquidacionPorcentajeObraCoreService()

    def verificar_editable(self, liquidacion_general: LiquidacionGeneral) -> None:
        """
        Guard de editabilidad por modo de cálculo (edge / MANUAL).

        Una liquidación MANUAL no es recalculable por tarifa: sus detalles se
        repartieron desde un subtotal manual y no tienen tarifa, porcentaje ni
        derecho. Recalcularla por tarifa sería matemáticamente imposible y
        semánticamente incorrecto.

        Se expone como método público para que el llamador pueda comprobar el
        guard ANTES de resolver el contexto de cálculo: así el error es el del
        guard (409) y no un error de validación de datos (400).

        Raises:
            ModoCalculoManualNoEditableError: la liquidación es MANUAL (409).
        """
        if liquidacion_general.modo_calculo == ModoCalculoLiquidacion.MANUAL:
            raise ModoCalculoManualNoEditableError(str(liquidacion_general.id))

    def recalcular(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchPorcentajeObraInput,
    ) -> LiquidacionPorcentajeObra:
        """
        Recalculate a PO liquidacion with optional patch inputs.

        All DB writes happen inside this method (caller wraps in transaction.atomic).

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched, with PO lock if needed).
            patch: Optional patch — valor_declarado and/or tarifas.

        Returns:
            Updated LiquidacionPorcentajeObra instance (caller should refresh).

        Raises:
            ModoCalculoManualNoEditableError: The liquidacion was created in
                MANUAL mode and cannot be recalculated by tariff (409).
            LiquidacionNoEncontradaError: No PO record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base at fecha_registro.
            NoDerechoVigenteError: No derecho at fecha_registro.
        """
        # ── 0. Row lock (SELECT ... FOR UPDATE) ─────────────────────────────────
        # Re-read the row under a row lock so two concurrent PATCH calls on the
        # same liquidacion are serialized: the second one waits for the first
        # transaction to commit instead of writing stale details on top of it.
        # The lock is taken INSIDE the transaction opened by the caller — this
        # core service never owns a transaction (contract §4.3).
        liquidacion_general = self.bloquear_liquidacion_general(liquidacion_general)

        # ── 0b. Guard: MANUAL (edge) liquidaciones are not recalculable ────────
        # A MANUAL liquidacion has no tarifa/porcentaje/derecho: running the
        # tariff engine over it would raise TypeError (HTTP 500). Reject it
        # explicitly with 409 instead.
        self.verificar_editable(liquidacion_general)

        # ── 1. Get PO record ───────────────────────────────────────────────────
        try:
            liq_po = liquidacion_general.liquidacion_porcentaje_obra
        except LiquidacionPorcentajeObra.DoesNotExist:
            raise LiquidacionNoEncontradaError(str(liquidacion_general.id))

        # ── 2. Resolve historical financial variables ───────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        igv = self._historico_service.get_igv_por_fecha(fecha)
        uit = self._historico_service.get_uit_por_fecha(fecha)
        derecho = self._historico_service.get_derecho_porcentaje_vigente(fecha)

        # ── 3. Determine valor_declarado ──────────────────────────────────────
        # Camino LEGACY (Taludes, Impacto Vial): se preserva el valor actual.
        # El camino por ESTRATEGIA resuelve el valor/total dentro del contexto
        # canónico (cada estrategia usa un dato distinto y excluye el otro).
        valor_declarado = patch.valor_declarado
        if valor_declarado is None:
            valor_declarado = liq_po.valor_declarado

        # ── 4. Determine tarifas to apply ─────────────────────────────────────
        if patch.tarifas is not None:
            # Explicit tariff list provided — build DTOs from input
            if patch.tarifas:
                tarifas_aplicadas = self._build_tarifa_dtos_from_input(patch.tarifas, fecha)
            else:
                # Empty list = no tarifas — must raise since calcular_cotizacion_po requires at least one
                raise BusinessError(
                    "Se requiere al menos una tarifa para recalcular la liquidacion."
                )
        elif patch.estrategia is None:
            # None = preserve current — rebuild DTOs from existing detail rows
            tarifas_aplicadas = self._build_tarifa_dtos_from_existing_details(liq_po)
        else:
            # Camino por estrategia: se preservan los participantes actuales,
            # pero el porcentaje unitario puede ser NULL (TOTAL_EXPLICITO
            # persiste los porcentajes en NULL) → se resuelve con el snapshot
            # `porcentaje_tarifa` del padre.
            tarifas_aplicadas = self._build_estrategia_dtarifas_from_existing_details(
                liq_po
            )

        # ── 5. Recalculate ───────────────────────────────────────────────────
        if patch.estrategia is None:
            # Camino LEGACY (Taludes, Impacto Vial): la aritmética y los efectos
            # sobre la base de datos quedan EXACTAMENTE como antes.
            cotizacion = self._po_core.calcular_cotizacion_po(
                valor_declarado=valor_declarado,
                tarifas=tarifas_aplicadas,
                igv_porcentaje=igv.valor,
                derecho=derecho,
                uit_valor=Decimal(str(uit.valor)),
            )
        else:
            # Camino por ESTRATEGIA (Edificaciones): el motor único decide la
            # aritmética según la estrategia cotizada y su ciclo de acumulación.
            cotizacion = self._po_core.calcular_cotizacion_po_estrategia(
                self._construir_contexto_estrategia(
                    patch=patch,
                    liq_po=liq_po,
                    valor_declarado=valor_declarado,
                    tarifas_aplicadas=tarifas_aplicadas,
                    igv_porcentaje=igv.valor,
                    uit_valor=Decimal(str(uit.valor)),
                    derecho=derecho,
                )
            )

        # ── 6. Delete + recreate details atomically ───────────────────────────
        # django-simple-history creates HistoricalRecords for deleted rows — expected.
        if patch.estrategia is None:
            liq_po.detalles.all().delete()

            for detalle in cotizacion.detalles:
                tarifa = detalle.tarifa_aplicada
                LiquidacionPorcentajeObraDetalle.objects.create(
                    liquidacion_porcentaje=liq_po,
                    tarifa_aplicada_id=tarifa.tarifa_id,
                    especialidad_id=tarifa.especialidad_id,
                    porcentaje_aplicado=detalle.porcentaje_aplicado,
                    subtotal=detalle.subtotal,
                    # `importe_parcial` / `ajuste_redondeo` MUST be persisted: they
                    # are the amounts the RH/CODEMU consumers read
                    # (finanzas_core_service.get_importes_po_detalle). Leaving them
                    # NULL makes every delegated honorario read 0.00 after an edit.
                    importe_parcial=detalle.importe_parcial,
                    ajuste_redondeo=detalle.ajuste_redondeo,
                )

            # ── 7. Update parent PO ───────────────────────────────────────────
            liq_po.valor_declarado = valor_declarado
            if patch.tipo_tramite is not None:
                liq_po.tipo_tramite = patch.tipo_tramite
            liq_po.porcentaje_liquidacion = cotizacion.porcentaje_liquidacion
            liq_po.derecho_minimo = cotizacion.derecho_minimo
            liq_po.derecho_maximo = cotizacion.derecho_maximo
            liq_po.porcentaje_minimo_uit = cotizacion.porcentaje_minimo_uit
            liq_po.derecho_aplicado = derecho
            liq_po.save()
        else:
            # Camino por estrategia: el padre, sus snapshots, sus detalles y la
            # fila de acumulación se reemplazan por la proyección del motor
            # (nada obsoleto sobrevive; la acumulación se crea/actualiza/elimina).
            self._po_core.aplicar_cotizacion_estrategia_po(
                liquidacion_po=liq_po,
                cotizacion=cotizacion,
                derecho=derecho,
                tipo_tramite=patch.tipo_tramite,
                count_habilitadas=patch.count_habilitadas,
            )

        # ── 8. Update LiquidacionGeneral totals ───────────────────────────────
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.igv_snapshot = igv.valor
        liquidacion_general.uit_snapshot = Decimal(str(uit.valor))
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit
        liquidacion_general.save()

        return liq_po

    def _construir_contexto_estrategia(
        self,
        patch: PatchPorcentajeObraInput,
        liq_po: LiquidacionPorcentajeObra,
        valor_declarado: Optional[Decimal],
        tarifas_aplicadas: list[TarifaPorcentajeObraAplicada],
        igv_porcentaje: Decimal,
        uit_valor: Decimal,
        derecho,
    ):
        """
        Construye el contexto canónico del motor único para la edición.

        No contiene fórmulas: sólo resuelve y entrega los valores YA resueltos
        (estrategia, H, valor declarado, total explícito, IGV, UIT y derechos
        por la fecha efectiva de la liquidación).

        Todas las estrategias conservan el valor declarado. TOTAL_EXPLICITO
        además usa el total final autoritativo para el cálculo.

        Los campos del snapshot que el llamador no envía se preservan del PO.
        """
        from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
        from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
            CotizacionPOContexto,
        )

        if patch.estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            valor_declarado_contexto = valor_declarado
            total_explicito = (
                patch.total_explicito
                if patch.total_explicito is not None
                else liq_po.total_explicito
            )
        else:
            valor_declarado_contexto = valor_declarado
            total_explicito = None

        return CotizacionPOContexto(
            estrategia=patch.estrategia,
            participantes=tarifas_aplicadas,
            count_habilitadas=patch.count_habilitadas,
            valor_declarado=valor_declarado_contexto,
            total_explicito=total_explicito,
            igv_porcentaje=igv_porcentaje,
            uit_valor=uit_valor,
            derecho=self._po_core.derecho_a_contexto(derecho),
        )

    def _build_estrategia_dtarifas_from_existing_details(
        self, liq_po: LiquidacionPorcentajeObra
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Reconstruye los DTOs de participantes desde los detalles actuales,
        preservando el estado persistido de la liquidación.

        A diferencia del camino legacy, el porcentaje unitario puede ser NULL:
        en TOTAL_EXPLICITO los porcentajes se persisten en NULL (invariante
        I-3). En ese caso se resuelve con el snapshot `porcentaje_tarifa` del
        padre y, en último caso, con el porcentaje vigente de la tarifa.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            TarifaPorcentajeObra,
        )

        porcentaje_snapshot = liq_po.porcentaje_tarifa

        dtos = []
        for detalle in liq_po.detalles.all():
            porcentaje = detalle.porcentaje_aplicado
            if porcentaje is None:
                porcentaje = porcentaje_snapshot
            if porcentaje is None and detalle.tarifa_aplicada_id:
                porcentaje = (
                    TarifaPorcentajeObra.objects.filter(id=detalle.tarifa_aplicada_id)
                    .values_list("porcentaje_liquidacion", flat=True)
                    .first()
                )
            if porcentaje is None:
                raise BusinessError(
                    "No se pudo determinar el porcentaje de la tarifa aplicada.",
                    code="PO_PORCENTAJE_TARIFA_AUSENTE",
                )
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(detalle.tarifa_aplicada_id),
                    porcentaje_liquidacion=porcentaje,
                    especialidad_id=str(detalle.especialidad_id),
                    especialidad_nombre=None,
                )
            )
        return dtos

    def bloquear_liquidacion_general(
        self, liquidacion_general: LiquidacionGeneral
    ) -> LiquidacionGeneral:
        """
        Refresh the LiquidacionGeneral under a row lock (SELECT ... FOR UPDATE).

        The lock serializes concurrent recalculations of the same liquidacion:
        the second writer blocks until the first transaction commits, so details
        can never be left half-written or stale.

        The refresh happens IN PLACE on the instance handed over by the caller,
        so the caller keeps working with the very same object and always sees
        the values the recalculation was based on. It also drops the stale
        prefetch cache of the instance (the caller's queryset may have
        prefetched the PO and its details before the lock was taken).

        The lock is only effective while the caller's transaction is open, so
        this method MUST be invoked from inside a transaction.atomic() block —
        the orchestrator/flujo owns the transaction, this core service never
        opens one (django-app-architecture-contract.md §4.3). When the caller is
        not inside a transaction the row is still refreshed, only without the
        lock clause, so the recalculation never breaks.

        Args:
            liquidacion_general: The instance handed over by the caller.

        Returns:
            The same instance, refreshed (and locked when possible).
        """
        queryset = LiquidacionGeneral.objects
        if transaction.get_connection().in_atomic_block:
            queryset = queryset.select_for_update()
        liquidacion_general.refresh_from_db(from_queryset=queryset)
        return liquidacion_general

    def _build_tarifa_dtos_from_input(
        self, tarifas: list[TarifaPatchInput], fecha: date
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Build TarifaPorcentajeObraAplicada DTOs from explicit patch input.

        Validates that each TarifaPorcentajeObra's TarifaLiquidacionBase is vigente
        at fecha (historical date of the liquidacion). Raises NoTarifaVigenteError
        if a provided tariff is not vigente for the historical date.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            TarifaPorcentajeObra,
            TarifaLiquidacionBase,
        )
        from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
            NoTarifaVigenteError,
        )

        dtos = []
        vigente_bases = set(
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha).values_list("id", flat=True)
        )
        for inp in tarifas:
            tarifa_po = TarifaPorcentajeObra.objects.select_related("tarifa_base").get(
                id=inp.tarifa_id
            )
            if tarifa_po.tarifa_base_id not in vigente_bases:
                raise NoTarifaVigenteError(
                    tarifa_po.tarifa_base.tipo_liquidacion.codigo, fecha
                )
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(tarifa_po.id),
                    porcentaje_liquidacion=tarifa_po.porcentaje_liquidacion,
                    especialidad_id=str(inp.especialidad_id),
                    especialidad_nombre=None,
                )
            )
        return dtos

    def _build_tarifa_dtos_from_existing_details(
        self, liq_po: LiquidacionPorcentajeObra
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Rebuild TarifaPorcentajeObraAplicada DTOs from existing detail rows.

        Preserves the currently applied percentages (detalle.porcentaje_aplicado)
        so recalculation uses the same rates that were originally applied.
        Only the tariff IDs are used to fetch the latest percentage_liquidacion
        from the tariff record (in case it changed), but the detail's stored
        percentage is used in the DTO to ensure the calculation is stable.
        """
        dtos = []
        for detalle in liq_po.detalles.all():
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(detalle.tarifa_aplicada_id),
                    porcentaje_liquidacion=detalle.porcentaje_aplicado,
                    especialidad_id=str(detalle.especialidad_id),
                    especialidad_nombre=None,
                )
            )
        return dtos
