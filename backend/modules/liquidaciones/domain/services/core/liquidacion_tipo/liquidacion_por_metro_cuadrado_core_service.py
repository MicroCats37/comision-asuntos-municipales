"""
LiquidacionPorMetroCuadradoCoreService — sync ORM operations for M2 calculations.

PURE ORM — no business logic beyond arithmetic.
Handles: TarifaPorMetroCuadrado, DerechoPorMetroCuadrado, LiquidacionPorMetroCuadrado, CotizacionM2.
"""
from decimal import Decimal
from typing import Optional

from ninja.errors import HttpError

from modules.liquidaciones.domain.models.liquidacion.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
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
            .filter(tipo_liquidacion=tipo_liquidacion)
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
            .filter(tarifa_base__tipo_liquidacion=tipo_liquidacion)
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
    ) -> CotizacionM2Result:
        """
        Calcula la cotización por metro cuadrado utilizando las vigencias de BD.
        """
        try:
            tarifa = TarifaPorMetroCuadradoModel.objects.select_related("tarifa_base").get(id=tarifa_m2_id)
        except TarifaPorMetroCuadradoModel.DoesNotExist:
            tarifa = self.get_tarifa_m2_vigente(tipo_liquidacion)

        if not tarifa:
            raise HttpError(400, f"No se encontró una tarifa vigente para {tipo_liquidacion}")

        derecho = self.get_derecho_minimo_m2_vigente()
        if not derecho:
            raise HttpError(400, "No se encontró configurado un Derecho mínimo vigente")

        monto_bruto = Decimal(str(area_solicitada)) * tarifa.costo_por_m2

        subtotal = monto_bruto
        if subtotal < derecho.derecho_minimo:
            subtotal = derecho.derecho_minimo

        if derecho.derecho_maximo is not None and subtotal > derecho.derecho_maximo:
            subtotal = derecho.derecho_maximo

        total = subtotal

        return CotizacionM2Result(
            area_m2=float(area_solicitada),
            costo_por_m2=float(tarifa.costo_por_m2),
            tarifa_id=str(tarifa.id),
            derecho_id=str(derecho.id),
            minimo=float(derecho.derecho_minimo),
            maximo=float(derecho.derecho_maximo) if derecho.derecho_maximo is not None else None,
            monto_bruto=float(monto_bruto),
            subtotal=float(subtotal),
            total=float(total),
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
