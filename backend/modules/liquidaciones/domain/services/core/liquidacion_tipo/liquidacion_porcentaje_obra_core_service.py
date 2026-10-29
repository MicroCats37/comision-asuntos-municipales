"""
Servicio core para cálculos de PorcentajeObra (PorcentajeObra).

ORM puro + aritmética. Sin @transaction.atomic, sin reglas de negocio.
(HttpError se usa únicamente como guard de validación de entrada, ver nota en calcular_cotizacion_po.)

MOTOR ÚNICO DE COTIZACIÓN POR ESTRATEGIA
========================================
`calcular_cotizacion_po_estrategia(contexto)` es el único motor aritmético del
motor PO de Edificaciones. Recibe un contexto tipado ya RESUELTO (estrategia,
universo de cobro H, participantes n, valor declarado o total explícito, IGV,
UIT y derechos) y devuelve la proyección efímera: padre + detalles + acumulación.

Reglas del motor (invariantes normativos del change):

- I-1  subtotal del padre == SUM(detalles) + acumulacion.subtotal_acumulado
- I-2  (modo 2) porcentaje del padre == SUM(detalles.porcentaje_aplicado)
       + acumulacion.porcentaje_acumulado
- I-3  (modo 3) padre/detalle/acumulación sin porcentaje (NULL)
- I-4  (modo 1) nunca existe acumulación
- I-5  no existe acumulación con diferencia cero

El motor NO consulta la base de datos: los valores históricos (IGV, UIT,
derechos, tarifa) los resuelve el llamador y se los entrega ya resueltos, de
modo que la edición conserva el contrato histórico por `fecha_registro`.

`calcular_cotizacion_po` se conserva como FACHADA de compatibilidad (Taludes,
Impacto Vial, import legacy y tests) y delega en el motor con la estrategia
`NORMAL_SELECCIONADAS`, sin cambiar una sola cifra.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Union
from ninja.errors import HttpError
from pydantic import Field

from core.exceptions import BusinessError
from core.types import BaseSchema

from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO, TipoLiquidacion

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorcentajeObra,
    TarifaLiquidacionBase,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    DatosPorcentajeObra,
    TarifaPorcentajeObraAplicada,
    LiquidacionPorcentajeObraData,
    DetallePorcentajeObraData,
    CotizacionPorcentajeObraData,
)


# ── Tipos canónicos del motor único de cotización PO ────────────────────────────

# Sentinel: distingue "H no resuelto" (None explícito) de "usar el valor del motor".
# Permite que la edición persista el snapshot de H EXACTO que resolvió el
# llamador (contrato de snapshot/catálogo) sin que el motor lo deduzca de los
# participantes (invariante: H NUNCA se deduce de n).
SIN_HABILITADAS_RESUELTAS = object()


class DerechoPOCotizacion(BaseSchema):
    """
    Derechos (mínimo/máximo) ya resueltos para la fecha efectiva.

    El motor NO consulta el catálogo: recibe los derechos resueltos por el
    llamador (vigentes hoy en creación, históricos por `fecha_registro` en
    edición). Así se preserva el contrato histórico para los callers de edición.
    """
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal = Decimal("0")
    derecho_aplicado_id: Optional[str] = None


class AcumulacionPOCotizacion(BaseSchema):
    """
    Proyección efímera de la diferencia entre el padre y la suma de sus detalles.

    `porcentaje_acumulado` es NULL en TOTAL_EXPLICITO (el total es autoritativo y
    no hay invariante de porcentaje). `subtotal_acumulado` es siempre monetario.
    """
    porcentaje_acumulado: Optional[Decimal] = None
    subtotal_acumulado: Decimal


class CotizacionPOContexto(BaseSchema):
    """
    Entrada canónica del motor único de cotización PO.

    Todo llega RESUELTO: la estrategia, el universo de cobro (H), el conjunto de
    participantes (n), el valor declarado o el total explícito, el IGV, la UIT y
    los derechos. El motor no consulta la base de datos ni "hoy": recibe los
    valores que el llamador resolvió para la fecha efectiva de la liquidación.
    """
    estrategia: str = EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
    participantes: List[TarifaPorcentajeObraAplicada] = Field(default_factory=list)
    count_habilitadas: Optional[int] = Field(
        default=None,
        description="H (habilitadas del catálogo en la fecha efectiva). "
        "Obligatorio en TARIFA_HABILITADAS_PARTICIPANTES y TOTAL_EXPLICITO.",
    )
    porcentaje_tarifa: Optional[Decimal] = Field(
        default=None,
        description="Porcentaje unitario (f) de la tarifa aplicable al padre.",
    )
    valor_declarado: Optional[Decimal] = None
    total_explicito: Optional[Decimal] = Field(
        default=None, description="Total final autoritativo con IGV (modo 3)."
    )
    igv_porcentaje: Decimal = Decimal("0")
    uit_valor: Decimal = Decimal("0")
    derecho: DerechoPOCotizacion
    override_subtotal: Optional[Decimal] = None
    override_total: Optional[Decimal] = None


class CotizacionPOEstrategiaData(BaseSchema):
    """
    Salida canónica del motor único de cotización PO.

    Proyección efímera: el padre, sus detalles y la acumulación. Este módulo NO
    persiste nada; la persistencia de la acumulación es responsabilidad de los
    módulos de create/edit.
    """
    estrategia: str
    valor_declarado: Optional[Decimal] = None
    total_explicito: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    porcentaje_tarifa: Optional[Decimal] = None
    tipo_tramite: Optional[str] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[str] = None
    count_habilitadas: int = 0
    count_participantes: int = 0
    detalles: List[DetallePorcentajeObraData] = Field(default_factory=list)
    total_subtotal: Decimal
    total: Decimal
    igv_monto: Decimal = Decimal("0.00")
    acumulacion: Optional[AcumulacionPOCotizacion] = None


class LiquidacionPorcentajeObraCoreService:
    """Service for PorcentajeObra motor calculations and ORM operations."""

    def resolver_tarifas(
        self,
        payload_tarifas_ids: List[str],
        tipo_liquidacion: str,
    ) -> List[TarifaPorcentajeObra]:
        """
        Hybrid resolution: empty list → auto-fill, non-empty → validate each.

        Returns the list of TarifaPorcentajeObra to apply.
        Caller (Orchestrator) is responsible for raising HttpError on invalid tarifas.

        Args:
            payload_tarifas_ids: List of tariff IDs to validate, or empty for auto-fill.
            tipo_liquidacion: The liquidacion type (e.g., TipoLiquidacion.EDIFICACION).

        Note: With tarifa-unica-especialidades, TarifaPorcentajeObra no longer has
        especialidad FK. Caller receives ORM objects (for validation) but must build
        TarifaPorcentajeObraAplicada DTOs with explicit especialidad from input.
        """
        if not payload_tarifas_ids:
            # Auto-fill mode: get all vigentes for the specified tipo_liquidacion
            bases = TarifaLiquidacionBase.objects.vigentes().filter(
                tipo_liquidacion__codigo=tipo_liquidacion
            )
            return list(
                TarifaPorcentajeObra.objects.filter(
                    tarifa_base__in=bases
                ).select_related("tarifa_base")
            )
        else:
            # Explicit mode: fetch and return for validation
            return list(
                TarifaPorcentajeObra.objects.filter(
                    id__in=payload_tarifas_ids
                ).select_related("tarifa_base")
            )
    
    def get_derecho_porcentaje_vigente(self) -> DerechoPorcentajeObra:
        """Returns the current vigente DerechoPorcentajeObra."""
        return DerechoPorcentajeObra.objects.vigentes().first()
    
    def get_tarifas_porcentaje_vigentes(
        self, tipo_liquidacion: str, fecha=None
    ) -> List[TarifaPorcentajeObra]:
        """
        Returns vigentes TarifaPorcentajeObra for the specified tipo_liquidacion.

        Args:
            tipo_liquidacion: The liquidacion type (e.g., TipoLiquidacion.EDIFICACION).
            fecha: Optional date to check vigencia. Defaults to today.
        """
        bases = TarifaLiquidacionBase.objects.vigentes(fecha=fecha).filter(
            tipo_liquidacion__codigo=tipo_liquidacion
        )
        return list(
            TarifaPorcentajeObra.objects.filter(
                tarifa_base__in=bases
            ).select_related("tarifa_base")
        )
    
    def calcular_cotizacion_po(
        self,
        valor_declarado: Decimal,
        tarifas: List[TarifaPorcentajeObraAplicada],
        igv_porcentaje: Decimal,
        derecho: DerechoPorcentajeObra,
        uit_valor: Decimal,
        override_subtotal: Decimal | None = None,
        override_total: Decimal | None = None,
    ) -> CotizacionPorcentajeObraData:
        """
        FACHADA de compatibilidad del motor PO (Taludes, Impacto Vial, import
        legacy y tests).

        Delega en el motor único con la estrategia `NORMAL_SELECCIONADAS` y
        devuelve el DTO histórico. La aritmética NO cambia: es exactamente la
        que se implementaba antes de la introduction del motor por estrategia.

        With tarifa-unica-especialidades: `tarifas` is List[TarifaPorcentajeObraAplicada].
        These DTOs carry explicit especialidad_id/especialidad_nombre from the input
        (sourced from LiquidacionEspecialidadDisponibles) — NOT from TarifaPorcentajeObra.especialidad
        (that FK no longer exists).

        Steps (bypassed when override_subtotal is set):
        1. Sumar porcentajes de todas las tarifas (ej: 3 x 0.05% = 0.15%)
        2. subtotal_bruto = valor_declarado x porcentaje_total
        3. minimo = uit_valor x derecho.porcentaje_minimo_uit (aplica a la LIQUIDACION, no por tarifa)
        4. subtotal_total = max(subtotal_bruto, minimo)
        5. clamp a derecho_maximo si aplica
        6. Repartir subtotal_total proporcionalmente entre detalles
        7. igv = subtotal_total x igv_porcentaje
        8. total = subtotal_total + igv

        When both override_subtotal and override_total are set (legacy import path),
        Step 7-8 are also bypassed: total is used directly as the legacy source total.
        """
        if not tarifas:
            # NOTE: Validación de entrada; idealmente vive en el Orquestador/Flujo,
            # pero no existe excepción de dominio específica y se mantiene como guard aquí.
            raise HttpError(400, "Se requiere al menos una tarifa")

        contexto = CotizacionPOContexto(
            estrategia=EstrategiaCotizacionPO.NORMAL_SELECCIONADAS,
            participantes=tarifas,
            valor_declarado=valor_declarado,
            igv_porcentaje=igv_porcentaje,
            uit_valor=uit_valor,
            derecho=self.derecho_a_contexto(derecho),
            override_subtotal=override_subtotal,
            override_total=override_total,
        )
        cotizacion = self.calcular_cotizacion_po_estrategia(contexto)

        return CotizacionPorcentajeObraData(
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            tipo_tramite=cotizacion.tipo_tramite,  # tipo_tramite se pasa directamente a create_liquidacion_porcentaje_obra
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado_id=cotizacion.derecho_aplicado_id,
            detalles=cotizacion.detalles,
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )

    # ── Motor único de cotización por estrategia ──────────────────────────────

    def calcular_cotizacion_po_estrategia(
        self, contexto: CotizacionPOContexto
    ) -> CotizacionPOEstrategiaData:
        """
        MOTOR ÚNICO de cotización PO.

        Recibe el contexto ya resuelto y devuelve la proyección efímera
        (padre + detalles + acumulación). Es la única fuente de aritmética del
        motor PO: preview, creación y edición deben invocar este método.

        - NORMAL_SELECCIONADAS: las seleccionadas determinan padre y detalles;
          nunca acumula (I-4).
        - TARIFA_HABILITADAS_PARTICIPANTES: el padre cobra H habilitadas y cada
          participante recibe la cuota `subtotal_padre / H`; la diferencia no
          distribuida se proyecta como acumulación (I-1, I-2).
        - TOTAL_EXPLICITO: el total con IGV es autoritativo; se extrae el
          subtotal, se reparte `subtotal / H` y los porcentajes quedan NULL (I-3).

        Los invariantes se verifican ANTES de devolver (verificar_invariantes_po).
        """
        estrategia = contexto.estrategia
        if contexto.valor_declarado is None or contexto.valor_declarado <= 0:
            raise BusinessError(
                "El valor declarado debe ser mayor a cero.",
                code="PO_VALOR_DECLARADO_INVALIDO",
            )

        if estrategia == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS:
            cotizacion = self._calcular_estrategia_normal(contexto)
        elif estrategia == EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES:
            cotizacion = self._calcular_estrategia_tarifa_habilitadas(contexto)
        elif estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            cotizacion = self._calcular_estrategia_total_explicito(contexto)
        else:
            raise BusinessError(
                f"Estrategia de cotización no soportada: {estrategia}",
                code="PO_ESTRATEGIA_NO_SOPORTADA",
            )

        self.verificar_invariantes_po(cotizacion)
        return cotizacion

    def verificar_invariantes_po(self, cotizacion: CotizacionPOEstrategiaData) -> None:
        """
        Verifica los invariantes normativos de la cotización PO.

        - I-1  subtotal del padre == SUM(detalles) + acumulacion.subtotal_acumulado
        - I-2  (modo 2) porcentaje del padre == SUM(detalles.porcentaje_aplicado)
               + acumulacion.porcentaje_acumulado
        - I-3  (modo 3) padre, detalle y acumulación sin porcentaje (NULL)
        - I-4  (modo 1) no existe acumulación
        - I-5  no existe acumulación con diferencia cero

        Levanta `BusinessError` (400) antes de cualquier commit: nunca se
        persisten números que no cierran.
        """
        suma_detalles = sum((d.subtotal for d in cotizacion.detalles), Decimal("0"))

        if cotizacion.count_participantes != len(cotizacion.detalles):
            raise BusinessError(
                "La cantidad de participantes no coincide con el número de detalles.",
                code="PO_INVARIANTE_CANTIDAD_PARTICIPANTES",
            )

        if cotizacion.total_subtotal < 0:
            raise BusinessError(
                "El subtotal del padre no puede ser negativo.",
                code="PO_INVARIANTE_NO_NEGATIVO",
            )
        for detalle in cotizacion.detalles:
            if detalle.subtotal < 0:
                raise BusinessError(
                    "El subtotal de un detalle no puede ser negativo.",
                    code="PO_INVARIANTE_NO_NEGATIVO",
                )

        if cotizacion.acumulacion is not None:
            if cotizacion.acumulacion.subtotal_acumulado < 0:
                raise BusinessError(
                    "La acumulación no puede ser negativa.",
                    code="PO_INVARIANTE_NO_NEGATIVO",
                )
            if cotizacion.acumulacion.subtotal_acumulado == 0:
                raise BusinessError(
                    "No se admite una acumulación con diferencia cero.",
                    code="PO_INVARIANTE_ACUMULACION_CERO",
                )
            total_conservado = suma_detalles + cotizacion.acumulacion.subtotal_acumulado
        else:
            total_conservado = suma_detalles

        if total_conservado != cotizacion.total_subtotal:
            raise BusinessError(
                "El subtotal del padre ({}) no coincide con la suma de los detalles "
                "más la acumulación ({}).".format(
                    cotizacion.total_subtotal, total_conservado
                ),
                code="PO_INVARIANTE_SUBTOTAL",
            )

        if cotizacion.estrategia == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS:
            if cotizacion.acumulacion is not None:
                raise BusinessError(
                    "NORMAL_SELECCIONADAS no genera acumulación.",
                    code="PO_INVARIANTE_SIN_ACUMULACION",
                )

        if cotizacion.estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            if cotizacion.porcentaje_liquidacion is not None:
                raise BusinessError(
                    "TOTAL_EXPLICITO no admite porcentaje en el padre.",
                    code="PO_INVARIANTE_PORCENTAJES_NULL",
                )
            for detalle in cotizacion.detalles:
                if detalle.porcentaje_aplicado is not None:
                    raise BusinessError(
                        "TOTAL_EXPLICITO no admite porcentaje en el detalle.",
                        code="PO_INVARIANTE_PORCENTAJES_NULL",
                    )
            if (
                cotizacion.acumulacion is not None
                and cotizacion.acumulacion.porcentaje_acumulado is not None
            ):
                raise BusinessError(
                    "TOTAL_EXPLICITO no admite porcentaje acumulado.",
                    code="PO_INVARIANTE_PORCENTAJES_NULL",
                )

        if cotizacion.estrategia == EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES:
            porcentaje_detalles = sum(
                (d.porcentaje_aplicado or Decimal("0") for d in cotizacion.detalles),
                Decimal("0"),
            )
            porcentaje_acumulado = (
                cotizacion.acumulacion.porcentaje_acumulado
                if cotizacion.acumulacion is not None
                else Decimal("0")
            ) or Decimal("0")
            if (
                cotizacion.porcentaje_liquidacion is None
                or porcentaje_detalles + porcentaje_acumulado != cotizacion.porcentaje_liquidacion
            ):
                raise BusinessError(
                    "El porcentaje del padre no coincide con la suma de los porcentajes "
                    "de detalle más el porcentaje acumulado.",
                    code="PO_INVARIANTE_PORCENTAJE",
                )

    # ── Estrategias ──────────────────────────────────────────────────────────

    def _calcular_estrategia_normal(
        self, contexto: CotizacionPOContexto
    ) -> CotizacionPOEstrategiaData:
        """
        NORMAL_SELECCIONADAS — las seleccionadas determinan el padre y los detalles.

        Es la aritmética vigente del motor PO, sin cambios: la suma de porcentajes
        de las seleccionadas define el padre, el piso UIT y el tope de derechos se
        aplican al padre, y el subtotal se reparte proporcionalmente entre los
        detalles (el último absorbe el resto de céntimos).

        Nunca genera acumulación (invariante I-4).
        """
        tarifas = list(contexto.participantes)
        if not tarifas:
            raise BusinessError(
                "Se requiere al menos una tarifa", code="PO_SIN_PARTICIPANTES"
            )

        # Paso 1-2: subtotal bruto agregado (NO por tarifa)
        porcentaje_total = sum(
            (t.porcentaje_liquidacion for t in tarifas), Decimal("0")
        )

        # Optional Legacy Totals Bypass: use Excel totals directly, skip Steps 1-5
        if contexto.override_subtotal is not None:
            subtotal_total = contexto.override_subtotal.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            if contexto.valor_declarado is None:
                raise BusinessError(
                    "El valor declarado es obligatorio para cotizar por tarifa.",
                    code="PO_VALOR_DECLARADO_INVALIDO",
                )
            subtotal_bruto = contexto.valor_declarado * porcentaje_total

            # Paso 3-4: minimo aplica a la liquidacion completa (UNA vez)
            minimo = contexto.uit_valor * contexto.derecho.porcentaje_minimo_uit
            subtotal_total = max(subtotal_bruto, minimo)

            # Paso 5: clamp a maximo si aplica
            if (
                contexto.derecho.derecho_maximo is not None
                and subtotal_total > contexto.derecho.derecho_maximo
            ):
                subtotal_total = contexto.derecho.derecho_maximo

        # Redondear el total a 2 decimales ANTES de repartir (moneda)
        subtotal_total = subtotal_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Paso 6: repartir proporcionalmente entre detalles.
        # El último detalle absorbe la diferencia de redondeo (remainder) para que
        # SUM(detalles.subtotal) == subtotal_total EXACTO (sin drift de céntimos).
        detalles = self._repartir_proporcional(tarifas, porcentaje_total, subtotal_total)

        # Paso 7-8: agregados GLOBALES (una sola vez sobre subtotal_total)
        total_subtotal = sum((d.subtotal for d in detalles), Decimal("0"))
        # Legacy bypass: when both override_subtotal and override_total are set,
        # use the legacy total directly (skip IGV recalculation).
        if contexto.override_subtotal is not None and contexto.override_total is not None:
            total = contexto.override_total.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            igv_monto = total - total_subtotal
        else:
            igv_monto = (total_subtotal * contexto.igv_porcentaje).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total = (total_subtotal + igv_monto).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return CotizacionPOEstrategiaData(
            estrategia=EstrategiaCotizacionPO.NORMAL_SELECCIONADAS,
            valor_declarado=contexto.valor_declarado,
            total_explicito=None,
            porcentaje_liquidacion=porcentaje_total,
            porcentaje_tarifa=self._resolver_porcentaje_tarifa(contexto),
            tipo_tramite=None,
            derecho_minimo=self._calcular_derecho_minimo(contexto),
            derecho_maximo=contexto.derecho.derecho_maximo,
            porcentaje_minimo_uit=contexto.derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=contexto.derecho.derecho_aplicado_id,
            count_habilitadas=(
                contexto.count_habilitadas
                if contexto.count_habilitadas is not None
                else len(tarifas)
            ),
            count_participantes=len(tarifas),
            detalles=detalles,
            total_subtotal=total_subtotal,
            total=total,
            igv_monto=igv_monto,
            acumulacion=None,
        )

    def _calcular_estrategia_tarifa_habilitadas(
        self, contexto: CotizacionPOContexto
    ) -> CotizacionPOEstrategiaData:
        """
        TARIFA_HABILITADAS_PARTICIPANTES — el padre cobra TODAS las habilitadas.

        - El padre se calcula sobre H habilitadas: `H × f`; el piso UIT y el tope
          de derechos se aplican al padre (la acumulación absorbe la diferencia).
        - Cada participante recibe la cuota monetaria proporcional `subtotal_padre / H`
          (su porción dentro del universo de H habilitadas).
        - La diferencia no distribuida se proyecta como acumulación, con porcentaje
          `(H − n) × f`, para que se cumpla el invariante I-2.
        """
        participantes = list(contexto.participantes)
        n = len(participantes)
        if n == 0:
            raise BusinessError(
                "Se requiere al menos un participante", code="PO_SIN_PARTICIPANTES"
            )

        habilitadas = self._resolver_habilitadas(contexto)
        if n > habilitadas:
            raise BusinessError(
                "La cantidad de participantes ({}) no puede superar la cantidad de "
                "habilitadas ({}).".format(n, habilitadas),
                code="PO_PARTICIPANTES_EXCEDEN_HABILITADAS",
            )

        if contexto.valor_declarado is None or contexto.valor_declarado <= 0:
            raise BusinessError(
                "El valor declarado debe ser mayor que cero.",
                code="PO_VALOR_DECLARADO_INVALIDO",
            )

        porcentaje_tarifa = self._resolver_porcentaje_tarifa(contexto)
        if porcentaje_tarifa is None:
            raise BusinessError(
                "No se pudo determinar el porcentaje de la tarifa aplicable.",
                code="PO_PORCENTAJE_TARIFA_AUSENTE",
            )
        # El padre cobra H habilitadas: H × f
        porcentaje_padre = Decimal(habilitadas) * porcentaje_tarifa

        subtotal_bruto = contexto.valor_declarado * porcentaje_padre
        minimo = contexto.uit_valor * contexto.derecho.porcentaje_minimo_uit
        subtotal_total = max(subtotal_bruto, minimo)
        if (
            contexto.derecho.derecho_maximo is not None
            and subtotal_total > contexto.derecho.derecho_maximo
        ):
            subtotal_total = contexto.derecho.derecho_maximo
        subtotal_total = subtotal_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        cuotas = self._repartir_por_habilitadas(subtotal_total, habilitadas, participantes)
        detalles = self._construir_detalles_cuota(cuotas, porcentaje_tarifa)
        suma_detalles = sum((d.subtotal for d in detalles), Decimal("0"))

        # La acumulación absorbe la diferencia entre el padre ajustado y lo
        # efectivamente distribuido a los participantes.
        subtotal_acumulado = subtotal_total - suma_detalles
        if subtotal_acumulado < 0:
            raise BusinessError(
                "El derecho máximo deja el subtotal del padre por debajo de la suma "
                "de los detalles: la diferencia no puede ser negativa.",
                code="PO_ACUMULACION_NEGATIVA",
            )

        porcentaje_detalles = sum(
            (d.porcentaje_aplicado or Decimal("0") for d in detalles), Decimal("0")
        )
        porcentaje_acumulado = porcentaje_padre - porcentaje_detalles
        acumulacion = self._construir_acumulacion(porcentaje_acumulado, subtotal_acumulado)

        igv_monto = (subtotal_total * contexto.igv_porcentaje).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = (subtotal_total + igv_monto).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return CotizacionPOEstrategiaData(
            estrategia=EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES,
            valor_declarado=contexto.valor_declarado,
            total_explicito=None,
            porcentaje_liquidacion=porcentaje_padre,
            porcentaje_tarifa=porcentaje_tarifa,
            tipo_tramite=None,
            derecho_minimo=self._calcular_derecho_minimo(contexto),
            derecho_maximo=contexto.derecho.derecho_maximo,
            porcentaje_minimo_uit=contexto.derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=contexto.derecho.derecho_aplicado_id,
            count_habilitadas=habilitadas,
            count_participantes=n,
            detalles=detalles,
            total_subtotal=subtotal_total,
            total=total,
            igv_monto=igv_monto,
            acumulacion=acumulacion,
        )

    def _calcular_estrategia_total_explicito(
        self, contexto: CotizacionPOContexto
    ) -> CotizacionPOEstrategiaData:
        """
        TOTAL_EXPLICITO — el total ingresado por el usuario es autoritativo.

        - El total incluye IGV: `S = T / (1 + g)` y `igv = T − S` (por resta, para
          que `S + igv == T` sea exacto al céntimo).
        - Cada participante recibe la cuota `S / H` (su porción del universo de H).
        - Los porcentajes (padre, detalle y acumulación) quedan NULL: el total es un
          dato autoritativo y no hay invariante de porcentaje (invariante I-3).
        - Los derechos se VALIDAN contra el subtotal previo al IGV: si el subtotal
          queda fuera del rango se RECHAZA. Nunca se eleva ni se ajusta el total.
        """
        participantes = list(contexto.participantes)
        n = len(participantes)
        if n == 0:
            raise BusinessError(
                "Se requiere al menos un participante", code="PO_SIN_PARTICIPANTES"
            )

        habilitadas = self._resolver_habilitadas(contexto)
        if n > habilitadas:
            raise BusinessError(
                "La cantidad de participantes ({}) no puede superar la cantidad de "
                "habilitadas ({}).".format(n, habilitadas),
                code="PO_PARTICIPANTES_EXCEDEN_HABILITADAS",
            )

        if contexto.total_explicito is None or contexto.total_explicito <= 0:
            raise BusinessError(
                "El total explícito debe ser mayor que cero.",
                code="PO_TOTAL_EXPLICITO_INVALIDO",
            )

        total_explicito = contexto.total_explicito.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # El IGV se extrae por RESTA para que subtotal + igv == total exacto.
        subtotal = (total_explicito / (Decimal("1") + contexto.igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        igv_monto = total_explicito - subtotal

        # Derechos: validación contra el subtotal previo al IGV (nunca elevación).
        minimo = contexto.uit_valor * contexto.derecho.porcentaje_minimo_uit
        if subtotal < minimo:
            raise BusinessError(
                "El subtotal ({}) es menor al derecho mínimo ({}).".format(
                    subtotal, minimo
                ),
                code="PO_TOTAL_EXPLICITO_BAJO_DERECHO_MINIMO",
            )
        if (
            contexto.derecho.derecho_maximo is not None
            and subtotal > contexto.derecho.derecho_maximo
        ):
            raise BusinessError(
                "El subtotal ({}) excede el derecho máximo ({}).".format(
                    subtotal, contexto.derecho.derecho_maximo
                ),
                code="PO_TOTAL_EXPLICITO_EXCEDE_DERECHO_MAXIMO",
            )

        cuotas = self._repartir_por_habilitadas(subtotal, habilitadas, participantes)
        # En TOTAL_EXPLICITO los porcentajes quedan NULL (invariante I-3).
        detalles = self._construir_detalles_cuota(cuotas, None)
        suma_detalles = sum((d.subtotal for d in detalles), Decimal("0"))

        subtotal_acumulado = subtotal - suma_detalles
        if subtotal_acumulado < 0:
            raise BusinessError(
                "La diferencia entre el subtotal y los detalles no puede ser negativa.",
                code="PO_ACUMULACION_NEGATIVA",
            )
        acumulacion = self._construir_acumulacion(None, subtotal_acumulado)

        return CotizacionPOEstrategiaData(
            estrategia=EstrategiaCotizacionPO.TOTAL_EXPLICITO,
            valor_declarado=contexto.valor_declarado,
            total_explicito=total_explicito,
            porcentaje_liquidacion=None,
            porcentaje_tarifa=self._resolver_porcentaje_tarifa(contexto),
            tipo_tramite=None,
            derecho_minimo=self._calcular_derecho_minimo(contexto),
            derecho_maximo=contexto.derecho.derecho_maximo,
            porcentaje_minimo_uit=contexto.derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=contexto.derecho.derecho_aplicado_id,
            count_habilitadas=habilitadas,
            count_participantes=n,
            detalles=detalles,
            total_subtotal=subtotal,
            total=total_explicito,
            igv_monto=igv_monto,
            acumulacion=acumulacion,
        )

    # ── Helpers de aritmética ────────────────────────────────────────────────

    def _repartir_proporcional(
        self,
        tarifas: List[TarifaPorcentajeObraAplicada],
        porcentaje_total: Decimal,
        subtotal_total: Decimal,
    ) -> List[DetallePorcentajeObraData]:
        """
        Reparte el subtotal del padre proporcionalmente entre los detalles.

        El último detalle absorbe la diferencia de redondeo (remainder) para que
        SUM(detalles.subtotal) == subtotal_total EXACTO (sin drift de céntimos).

        SHADOW MODE: `subtotal` se calcula IGUAL que antes para no romper lectores
        downstream. En paralelo se calculan los campos de alta precisión:
          - importe_parcial: valor teórico por especialidad, quantizado.
          - ajuste_redondeo: 0.00 para todos, el último recibe el remainder.
        """
        detalles: List[DetallePorcentajeObraData] = []
        n = len(tarifas)

        # Primera pasada: calcular importe_parcial teórico para cada detalle
        importe_parciales: List[Decimal] = []
        for tarifa_dto in tarifas:
            if porcentaje_total > 0:
                proporcion = tarifa_dto.porcentaje_liquidacion / porcentaje_total
            else:
                proporcion = Decimal("1") / Decimal(n)
            theoretical_value = subtotal_total * proporcion
            importe_parcial = theoretical_value.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            importe_parciales.append(importe_parcial)

        # Calcular el ajuste de redondeo total (remainder)
        suma_importe_parcial = sum(importe_parciales, Decimal("0"))
        ajuste_total = subtotal_total - suma_importe_parcial

        # Segunda pasada: construir los detalles definitivos
        for idx, tarifa_dto in enumerate(tarifas):
            if porcentaje_total > 0:
                proporcion = tarifa_dto.porcentaje_liquidacion / porcentaje_total
            else:
                proporcion = Decimal("1") / Decimal(n)

            if idx == n - 1:
                # Último detalle: absorber la diferencia para cuadrar la suma
                subtotal_detalle = subtotal_total - sum(
                    (d.subtotal for d in detalles), Decimal("0")
                )
            else:
                subtotal_detalle = (subtotal_total * proporcion).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            # Shadow Mode: nuevos campos de alta precisión
            importe_parcial = importe_parciales[idx]
            if idx == n - 1:
                ajuste_redondeo = ajuste_total
            else:
                ajuste_redondeo = Decimal("0.00")

            # With tarifa-unica: the DTO already has explicit especialidad from input.
            # El detalle SOLO lleva subtotal parcial — el IGV y el total se calculan
            # a nivel global (subtotal_total), NO por tarifa.
            detalles.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=tarifa_dto,  # already has especialidad_id/nombre
                    porcentaje_aplicado=tarifa_dto.porcentaje_liquidacion,
                    subtotal=subtotal_detalle,
                    importe_parcial=importe_parcial,
                    ajuste_redondeo=ajuste_redondeo,
                )
            )

        return detalles

    def _repartir_por_habilitadas(
        self,
        monto: Decimal,
        habilitadas: int,
        participantes: List[TarifaPorcentajeObraAplicada],
    ) -> List[Tuple[TarifaPorcentajeObraAplicada, Decimal]]:
        """
        Reparte `monto` entre los participantes con cuota proporcional `monto / H`.

        El reparto es ACUMULATIVO y canónico: la cuota del participante i (en orden
        estable por `especialidad_id` ascendente, decisión D-J) es
        `Q(monto × i / H) − Q(monto × (i − 1) / H)`.

        Garantiza cuotas no negativas y conservación exacta: la suma de las cuotas
        es `Q(monto × n / H)`, de modo que cuando `n == H` la suma es exactamente
        `monto` y no queda diferencia por acumular (invariante I-5).
        """
        total_h = Decimal(habilitadas)
        ordenados = sorted(
            participantes,
            key=lambda t: (str(t.especialidad_id), str(t.tarifa_id)),
        )

        cuotas: List[Tuple[TarifaPorcentajeObraAplicada, Decimal]] = []
        acumulado_previo = Decimal("0")
        for indice, participante in enumerate(ordenados, start=1):
            acumulado = (monto * Decimal(indice) / total_h).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            cuotas.append((participante, acumulado - acumulado_previo))
            acumulado_previo = acumulado

        return cuotas

    def _construir_detalles_cuota(
        self,
        cuotas: List[Tuple[TarifaPorcentajeObraAplicada, Decimal]],
        porcentaje_aplicado: Optional[Decimal],
    ) -> List[DetallePorcentajeObraData]:
        """
        Construye los detalles a partir de las cuotas del universo de habilitadas.

        `porcentaje_aplicado` es None en TOTAL_EXPLICITO (los porcentajes quedan
        NULL); en TARIFA_HABILITADAS_PARTICIPANTES es el porcentaje unitario f.
        """
        detalles: List[DetallePorcentajeObraData] = []
        for participante, cuota in cuotas:
            detalles.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=participante,
                    porcentaje_aplicado=porcentaje_aplicado,
                    subtotal=cuota,
                    importe_parcial=cuota,
                    ajuste_redondeo=Decimal("0.00"),
                )
            )
        return detalles

    def _construir_acumulacion(
        self,
        porcentaje_acumulado: Optional[Decimal],
        subtotal_acumulado: Decimal,
    ) -> Optional[AcumulacionPOCotizacion]:
        """
        Proyecta la acumulación. Si la diferencia es cero NO se proyecta fila
        (invariante I-5).
        """
        if subtotal_acumulado == 0:
            return None
        return AcumulacionPOCotizacion(
            porcentaje_acumulado=porcentaje_acumulado,
            subtotal_acumulado=subtotal_acumulado,
        )

    def _resolver_habilitadas(self, contexto: CotizacionPOContexto) -> int:
        """
        Resuelve H (habilitadas del catálogo en la fecha efectiva).

        H NUNCA se deduce de los participantes: es el universo de cobro y lo
        resuelve el llamador (catálogo por fecha efectiva o snapshot persistido).
        """
        if contexto.count_habilitadas is None:
            raise BusinessError(
                "No se resolvió la cantidad de especialidades habilitadas (H).",
                code="PO_HABILITADAS_NO_RESUELTAS",
            )
        if contexto.count_habilitadas <= 0:
            raise BusinessError(
                "No hay especialidades habilitadas para cotizar.",
                code="PO_SIN_HABILITADAS",
            )
        return contexto.count_habilitadas

    def _resolver_porcentaje_tarifa(
        self, contexto: CotizacionPOContexto
    ) -> Optional[Decimal]:
        """
        Resuelve el porcentaje unitario f de la tarifa aplicable al padre.

        Si el contexto no lo trae, se toma de la tarifa del primer participante
        (en el modelo de tarifa única todas las habilitadas comparten f).
        """
        if contexto.porcentaje_tarifa is not None:
            return contexto.porcentaje_tarifa
        if contexto.participantes:
            return contexto.participantes[0].porcentaje_liquidacion
        return None

    def _calcular_derecho_minimo(self, contexto: CotizacionPOContexto) -> Decimal:
        """
        Derecho mínimo reportado: si la tarifa no trae valor absoluto, se calcula
        como (UIT × porcentaje_minimo_uit) + IGV vigente, sin hardcodear.
        """
        derecho_minimo_calculado = (
            contexto.uit_valor
            * contexto.derecho.porcentaje_minimo_uit
            * (Decimal("1") + contexto.igv_porcentaje)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        derecho_minimo = contexto.derecho.derecho_minimo or derecho_minimo_calculado
        return derecho_minimo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def derecho_a_contexto(self, derecho) -> DerechoPOCotizacion:
        """Traduce el `DerechoPorcentajeObra` (ORM o equivalente) al tipo del motor."""
        return DerechoPOCotizacion(
            derecho_minimo=derecho.derecho_minimo,
            derecho_maximo=derecho.derecho_maximo,
            porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=(
                str(derecho.id) if getattr(derecho, "id", None) is not None else None
            ),
        )


    def create_liquidacion_porcentaje_obra(
        self,
        liquidacion_general,
        cotizacion: Union[CotizacionPorcentajeObraData, CotizacionPOEstrategiaData],
        derecho: DerechoPorcentajeObra,
        tipo_tramite: Optional[str] = None,
    ) -> LiquidacionPorcentajeObra:
        """
        Creates LiquidacionPorcentajeObra + all Detalles in DB.

        With tarifa-unica-especialidades: LiquidacionPorcentajeObraDetalle.especialidad
        is set from detalle.tarifa_aplicada.especialidad_id (explicit from input),
        NOT from TarifaPorcentajeObra.especialidad (FK removed).

        Si la cotización proviene del motor por estrategia
        (`CotizacionPOEstrategiaData`), se delega en
        `create_liquidacion_porcentaje_obra_estrategia`, que además persiste la
        estrategia, sus snapshots y la fila de acumulación. Los demás motores
        (Taludes, Impacto Vial, import legacy) siguen el camino histórico intacto.
        """
        if isinstance(cotizacion, CotizacionPOEstrategiaData):
            return self.create_liquidacion_porcentaje_obra_estrategia(
                liquidacion_general=liquidacion_general,
                cotizacion=cotizacion,
                derecho=derecho,
                tipo_tramite=tipo_tramite,
            )

        liquidacion_po = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion_general,
            tipo_tramite=tipo_tramite,
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado=derecho,
        )
        # Create detalles
        for detalle in cotizacion.detalles:
            tarifa = TarifaPorcentajeObra.objects.get(
                id=detalle.tarifa_aplicada.tarifa_id
            )
            LiquidacionPorcentajeObraDetalle.objects.create(
                liquidacion_porcentaje=liquidacion_po,
                tarifa_aplicada=tarifa,
                especialidad_id=detalle.tarifa_aplicada.especialidad_id,
                porcentaje_aplicado=detalle.porcentaje_aplicado,
                subtotal=detalle.subtotal,
                importe_parcial=detalle.importe_parcial,
                ajuste_redondeo=detalle.ajuste_redondeo,
            )
        return liquidacion_po

    def create_liquidacion_porcentaje_obra_estrategia(
        self,
        liquidacion_general,
        cotizacion: CotizacionPOEstrategiaData,
        derecho: DerechoPorcentajeObra,
        tipo_tramite: Optional[str] = None,
    ) -> LiquidacionPorcentajeObra:
        """
        Crea el PO padre con la estrategia y sus snapshots, sus detalles y la
        fila de acumulación (OneToOne) según el resultado de la cotización.

        Persistencia (sin fórmulas: la aritmética ya viene del motor único):

        - `estrategia_cotizacion`: la estrategia cotizada.
        - `count_habilitadas`: snapshot de H (habilitadas del catálogo).
        - `total_explicito`: total autoritativo (TOTAL_EXPLICITO).
        - `porcentaje_tarifa`: snapshot del porcentaje unitario (f) del padre.
        - `tarifa_aplicada`: tarifa que genera el subtotal del padre (puede no
          aparecer en ningún detalle en modo habilitadas).
        - acumulación: se crea si la diferencia no es cero; si la diferencia es
          cero NO existe fila (invariante I-5).

        La atomicidad la aporta el flujo (`transaction.atomic`): esta operación
        es parte de la misma transacción que crea el LiquidacionGeneral.
        """
        tarifa_padre = None
        if cotizacion.detalles:
            primera = cotizacion.detalles[0]
            if primera.tarifa_aplicada and primera.tarifa_aplicada.tarifa_id:
                tarifa_padre = TarifaPorcentajeObra.objects.filter(
                    id=primera.tarifa_aplicada.tarifa_id
                ).first()

        liquidacion_po = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion_general,
            tipo_tramite=tipo_tramite,
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            estrategia_cotizacion=str(cotizacion.estrategia),
            count_habilitadas=cotizacion.count_habilitadas,
            total_explicito=cotizacion.total_explicito,
            porcentaje_tarifa=cotizacion.porcentaje_tarifa,
            tarifa_aplicada=tarifa_padre,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado=derecho,
        )

        self.crear_detalles_porcentaje_obra(liquidacion_po, cotizacion.detalles)

        self.aplicar_acumulacion_po(liquidacion_po, cotizacion.acumulacion)
        return liquidacion_po

    def crear_detalles_porcentaje_obra(
        self,
        liquidacion_po: LiquidacionPorcentajeObra,
        detalles: List[DetallePorcentajeObraData],
    ) -> None:
        """
        Persiste los detalles de un PO a partir de la proyección del motor.

        NO contiene fórmulas: la aritmética ya viene del motor único
        (`calcular_cotizacion_po_estrategia`). Los campos de alta precisión
        (`importe_parcial` / `ajuste_redondeo`) SIEMPRE se persisten: son los
        importes que leen los consumidores RH/CODEMU
        (`finanzas_core_service.get_importes_po_detalle`); si quedaran NULL,
        cualquier edición anularía el honorario del delegado.
        """
        for detalle in detalles:
            tarifa = TarifaPorcentajeObra.objects.get(
                id=detalle.tarifa_aplicada.tarifa_id
            )
            LiquidacionPorcentajeObraDetalle.objects.create(
                liquidacion_porcentaje=liquidacion_po,
                tarifa_aplicada=tarifa,
                especialidad_id=detalle.tarifa_aplicada.especialidad_id,
                porcentaje_aplicado=detalle.porcentaje_aplicado,
                subtotal=detalle.subtotal,
                importe_parcial=detalle.importe_parcial,
                ajuste_redondeo=detalle.ajuste_redondeo,
            )

    def aplicar_cotizacion_estrategia_po(
        self,
        liquidacion_po: LiquidacionPorcentajeObra,
        cotizacion: CotizacionPOEstrategiaData,
        derecho,
        tipo_tramite: Optional[str] = None,
        count_habilitadas=SIN_HABILITADAS_RESUELTAS,
    ) -> LiquidacionPorcentajeObra:
        """
        Reemplaza el estado calculado de un PO EXISTENTE por la proyección del
        motor único (estrategia + snapshots + detalles + acumulación).

        Es el camino de EDICIÓN (PATCH) y de las transiciones de estrategia:

        - los detalles anteriores se ELIMINAN y se recrean desde el motor: no
          sobreviven detalles obsoletos ni con porcentajes de otra estrategia;
        - el padre queda con la estrategia y sus snapshots (`count_habilitadas`,
          `total_explicito`, `porcentaje_tarifa`, `tarifa_aplicada`);
        - la fila de acumulación se CREA, ACTUALIZA o ELIMINA según la
          diferencia (invariante I-5: nunca hay acumulación con diferencia cero).

        `count_habilitadas` permite al llamador fijar el snapshot de H EXACTO
        que resolvió (contrato de snapshot/catálogo). Por defecto se usa el
        que devolvió el motor.

        NO abre transacción propia: la atomicidad la aporta el flujo/orquestador
        (django-app-architecture-contract.md §4.3).
        """
        # ── 1. Reemplazar los detalles (nada obsoleto sobrevive) ────────────────
        liquidacion_po.detalles.all().delete()
        self.crear_detalles_porcentaje_obra(liquidacion_po, cotizacion.detalles)

        # ── 2. Padre: estrategia + snapshots + derechos ──────────────────────────
        tarifa_padre = None
        if cotizacion.detalles:
            primera = cotizacion.detalles[0]
            if primera.tarifa_aplicada and primera.tarifa_aplicada.tarifa_id:
                tarifa_padre = TarifaPorcentajeObra.objects.filter(
                    id=primera.tarifa_aplicada.tarifa_id
                ).first()

        liquidacion_po.valor_declarado = cotizacion.valor_declarado
        liquidacion_po.porcentaje_liquidacion = cotizacion.porcentaje_liquidacion
        liquidacion_po.estrategia_cotizacion = str(cotizacion.estrategia)
        liquidacion_po.count_habilitadas = (
            cotizacion.count_habilitadas
            if count_habilitadas is SIN_HABILITADAS_RESUELTAS
            else count_habilitadas
        )
        liquidacion_po.total_explicito = cotizacion.total_explicito
        liquidacion_po.porcentaje_tarifa = cotizacion.porcentaje_tarifa
        liquidacion_po.tarifa_aplicada = tarifa_padre
        liquidacion_po.derecho_minimo = cotizacion.derecho_minimo
        liquidacion_po.derecho_maximo = cotizacion.derecho_maximo
        liquidacion_po.porcentaje_minimo_uit = cotizacion.porcentaje_minimo_uit
        liquidacion_po.derecho_aplicado = derecho
        if tipo_tramite is not None:
            liquidacion_po.tipo_tramite = tipo_tramite
        liquidacion_po.save()

        # ── 3. Acumulación: create / update / delete ────────────────────────────
        self.aplicar_acumulacion_po(liquidacion_po, cotizacion.acumulacion)

        return liquidacion_po

    def aplicar_acumulacion_po(
        self,
        liquidacion_po: LiquidacionPorcentajeObra,
        acumulacion: Optional[AcumulacionPOCotizacion],
    ):
        """
        Ciclo de vida de la fila de acumulación (OneToOne referencial del PO).

        - con diferencia: crea o actualiza la fila vigente;
        - sin diferencia (diferencia cero): elimina la fila si existía
          (invariante I-5: nunca hay acumulación con diferencia cero).

        No abre transacción propia: la atomicidad la aporta el flujo.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
            LiquidacionPorcentajeObraAcumulacion,
        )

        if acumulacion is None:
            LiquidacionPorcentajeObraAcumulacion.objects.filter(
                liquidacion_porcentaje=liquidacion_po
            ).delete()
            return None

        fila, _ = LiquidacionPorcentajeObraAcumulacion.objects.update_or_create(
            liquidacion_porcentaje=liquidacion_po,
            defaults={
                "porcentaje_acumulado": acumulacion.porcentaje_acumulado,
                "subtotal_acumulado": acumulacion.subtotal_acumulado,
            },
        )
        return fila

    def calcular_cotizacion_po_edge(
        self,
        subtotal_manual: Decimal,
        especialidades: list,
        igv_porcentaje: Decimal,
    ) -> CotizacionPorcentajeObraData:
        """
        Calculate edge (manual) PO cotizacion — equal distribution among specialties.

        Called by the edge flow when modo_calculo=MANUAL. The subtotal_manual is
        pre-IGV and is distributed equally among the given specialties.

        Algorithm:
        1. subtotal_manual is pre-IGV (already the base for distribution)
        2. n = len(especialidades)
        3. base = (subtotal_manual / n).quantize(Decimal("0.01"), ROUND_HALF_UP)
        4. For i in 0..n-2: subtotal_detalle[i] = base
        5. subtotal_detalle[n-1] = subtotal_manual - sum(subtotales[0..n-2])
           (last specialty absorbs the rounding remainder)
        6. igv = subtotal_manual * igv_porcentaje
        7. total = subtotal_manual + igv

        Args:
            subtotal_manual: Decimal > 0 — pre-IGV subtotal
            especialidades: List of LiquidacionEspecialidadDisponibles ORM objects
                (each has especialidad_id attribute)
            igv_porcentaje: Decimal — IGV percentage (e.g. 0.18 for 18%)

        Returns:
            CotizacionPorcentajeObraData with valor_declarado=None, all percentages null,
            derecho fields null, and detalles with null tarifa_aplicada.
        """
        from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
            DetallePorcentajeObraData,
        )

        subtotal_total = subtotal_manual.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        n = len(especialidades)

        if n == 0:
            raise HttpError(400, "No hay especialidades para distribuir el subtotal")

        base = (subtotal_total / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        detalles: list[DetallePorcentajeObraData] = []
        for idx, esp in enumerate(especialidades):
            if idx == n - 1:
                # Last specialty absorbs rounding remainder
                subtotal_detalle = subtotal_total - sum(
                    d.subtotal for d in detalles
                )
            else:
                subtotal_detalle = base

            detalles.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=None,  # null in edge mode
                    porcentaje_aplicado=None,  # null in edge mode
                    subtotal=subtotal_detalle,
                    especialidad_id=str(esp.especialidad_id),
                )
            )

        igv = (subtotal_total * igv_porcentaje).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = (subtotal_total + igv).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return CotizacionPorcentajeObraData(
            valor_declarado=None,  # no aplica en modo manual
            porcentaje_liquidacion=None,  # null en edge
            tipo_tramite=None,
            derecho_minimo=None,
            derecho_maximo=None,
            porcentaje_minimo_uit=None,
            derecho_aplicado_id=None,  # null en edge
            detalles=detalles,
            total_subtotal=subtotal_total,
            total=total,
        )

    def create_liquidacion_porcentaje_obra_edge(
        self,
        liquidacion_general,
        cotizacion: CotizacionPorcentajeObraData,
        tipo_tramite: Optional[str] = None,
    ) -> LiquidacionPorcentajeObra:
        """
        Creates LiquidacionPorcentajeObra + all Detalles in DB for edge/manual mode.

        Difference from create_liquidacion_porcentaje_obra:
        - Does NOT fetch TarifaPorcentajeObra (tarifa_aplicada FK is null)
        - derecho_aplicado FK is null
        - porcentaje_liquidacion is null
        - valor_declarado is null

        Args:
            liquidacion_general: LiquidacionGeneral ORM instance
            cotizacion: CotizacionPorcentajeObraData from calcular_cotizacion_po_edge
            tipo_tramite: Optional[str]

        Returns:
            LiquidacionPorcentajeObra instance
        """
        liquidacion_po = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion_general,
            tipo_tramite=tipo_tramite,
            valor_declarado=None,  # null en edge
            porcentaje_liquidacion=None,  # null en edge
            derecho_minimo=None,
            derecho_maximo=None,
            porcentaje_minimo_uit=None,
            derecho_aplicado=None,  # null en edge
        )
        # Create detalles with null tarifa_aplicada
        for detalle in cotizacion.detalles:
            LiquidacionPorcentajeObraDetalle.objects.create(
                liquidacion_porcentaje=liquidacion_po,
                tarifa_aplicada=None,  # null en edge
                especialidad_id=detalle.especialidad_id,
                porcentaje_aplicado=None,  # null en edge
                subtotal=detalle.subtotal,
                importe_parcial=None,  # not used in edge
                ajuste_redondeo=None,  # not used in edge
            )
        return liquidacion_po
