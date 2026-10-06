"""
LiquidacionPorMetroCuadradoCoreService — operaciones ORM síncronas para cálculos M2.

ORM PURO — sin lógica de negocio más allá de la aritmética.
Maneja: TarifaPorMetroCuadrado, DerechoPorMetroCuadrado, LiquidacionPorMetroCuadrado, CotizacionM2.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado as TarifaPorMetroCuadradoModel,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result


class LiquidacionPorMetroCuadradoCoreService:
    """
    Core sync service for M2 tariff and calculation ORM operations.
    Reutilizable por cualquier especialidad basada en Metro Cuadrado.
    """

    def get_tarifa_vigente_por_tipo(
        self,
        tipo_liquidacion: str,
    ) -> Optional[TarifaLiquidacionBase]:
        """
        Get the currently active tariff base by tipo_liquidacion.
        """
        return (
            TarifaLiquidacionBase.objects.vigentes()
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .select_related("detalle_m2", "detalle_visitas")
            .first()
        )

    def get_tarifa_m2_vigente(
        self,
        tipo_liquidacion: str,
    ) -> Optional[TarifaPorMetroCuadradoModel]:
        """
        Get the currently active M2 tariff for a tipo_liquidacion.
        """
        return (
            TarifaPorMetroCuadradoModel.objects.select_related("tarifa_base")
            .filter(tarifa_base__tipo_liquidacion__codigo=tipo_liquidacion)
            .filter(tarifa_base__periodo_fin__isnull=True)
            .order_by("-tarifa_base__periodo_inicio")
            .first()
        )

    def get_derecho_minimo_m2_vigente(
        self,
    ) -> Optional[DerechoPorMetroCuadrado]:
        """
        Get the currently active minimum right for M2 calculations.
        """
        return (
            DerechoPorMetroCuadrado.objects.vigentes()
            .order_by("-periodo_inicio")
            .first()
        )

    def calcular_cotizacion_m2(
        self,
        tipo_liquidacion: str,
        area_solicitada: float,
        tarifa_m2_id: str,
        derecho: Optional[DerechoPorMetroCuadrado] = None,
        igv_porcentaje: Optional[Decimal] = None,
    ) -> CotizacionM2Result:
        """
        Calculates M2 quotation using BD vigencias.
        PURE computation - only arithmetic, no business logic validation.

        Formula (validated with user):
          total = area × costo_por_m2  (costo_por_m2 is BRUTO, already includes IGV)
          subtotal = total / (1 + igv_porcentaje)  — derived, rounded to 2 decimals
          monto_igv = total - subtotal  — by subtraction

        Args:
            derecho: Optional pre-resolved DerechoPorMetroCuadrado.
                    If None, resolves via vigentes() (current) — use for new creations.
                    If provided, uses the passed derecho — use for PATCH recalculation.
            igv_porcentaje: Decimal fraction (e.g. Decimal("0.18") for 18% IGV).
                           If None, subtotal=total=monto_bruto (no IGV derivation).
        """
        try:
            tarifa = TarifaPorMetroCuadradoModel.objects.select_related("tarifa_base").get(id=tarifa_m2_id)
        except TarifaPorMetroCuadradoModel.DoesNotExist:
            tarifa = self.get_tarifa_m2_vigente(tipo_liquidacion)

        if derecho is None:
            derecho = self.get_derecho_minimo_m2_vigente()

        monto_bruto = Decimal(str(area_solicitada)) * tarifa.costo_por_m2
        total = monto_bruto

        if igv_porcentaje is not None:
            subtotal = (total / (Decimal("1") + igv_porcentaje)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            monto_igv = total - subtotal
        else:
            subtotal = total
            monto_igv = Decimal("0")

        return CotizacionM2Result(
            area_m2=Decimal(str(area_solicitada)),
            costo_por_m2=tarifa.costo_por_m2,
            tarifa_id=str(tarifa.id),
            derecho_id=str(derecho.id) if derecho else None,
            minimo=derecho.derecho_minimo if derecho else None,
            maximo=derecho.derecho_maximo if derecho and derecho.derecho_maximo is not None else None,
            monto_bruto=monto_bruto,
            subtotal=subtotal,
            total=total,
            igv_porcentaje=igv_porcentaje,
            monto_igv=monto_igv,
        )

    def create_liquidacion_por_metro_cuadrado(
        self,
        liquidacion_general: LiquidacionGeneral,
        area_solicitada: float,
        tarifa_aplicada: TarifaPorMetroCuadradoModel,
        derecho_aplicado: DerechoPorMetroCuadrado,
        subtotal: Decimal,
        total: Decimal,
    ) -> LiquidacionPorMetroCuadrado:
        """
        Creates a LiquidacionPorMetroCuadrado linked to LiquidacionGeneral.
        """
        return LiquidacionPorMetroCuadrado.objects.create(
            liquidacion_general=liquidacion_general,
            area_m2=Decimal(str(area_solicitada)),
            costo_por_m2=tarifa_aplicada.costo_por_m2,
            derecho_minimo=derecho_aplicado.derecho_minimo,
            derecho_maximo=derecho_aplicado.derecho_maximo,
            tarifa_aplicada=tarifa_aplicada,
            derecho=derecho_aplicado,
        )

    def create_liquidacion_por_metro_cuadrado_edge(
        self,
        liquidacion_general: LiquidacionGeneral,
        area_solicitada: float,
        subtotal: Decimal,
        total: Decimal,
    ) -> LiquidacionPorMetroCuadrado:
        """
        Creates a LiquidacionPorMetroCuadrado for edge (manual) mode.

        In edge mode:
        - tarifa_aplicada is null (no tariff was used)
        - derecho is null (no derecho was applied)
        - costo_por_m2 is null (derived from tariff)
        - derecho_minimo/derecho_maximo are set to 0 (not applicable)

        All other fields are set normally.
        """
        return LiquidacionPorMetroCuadrado.objects.create(
            liquidacion_general=liquidacion_general,
            area_m2=Decimal(str(area_solicitada)),
            costo_por_m2=None,  # null for edge — not applicable
            derecho_minimo=Decimal("0"),
            derecho_maximo=None,
            tarifa_aplicada=None,  # null for edge — no tariff
            derecho=None,  # null for edge — no derecho
        )
