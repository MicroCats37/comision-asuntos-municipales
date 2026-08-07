"""
LiquidacionHabilitacionUrbanaOrchestrator — async facade for Habilitacion Urbana.

Thin async facade. Validates input and delegates to Core/Flujo for calculation.
"""
from injector import inject
from ninja.errors import HttpError
from asgiref.sync import sync_to_async

from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionHabilitacionUrbanaOrchestrator:
    """
    Async facade for Habilitacion Urbana liquidacion.

    Responsibilities:
    - Input validation (area_solicitada > 0)
    - Delegates to M2 Core service for calculation
    """

    @inject
    def __init__(self, m2_core_service: LiquidacionPorMetroCuadradoCoreService):
        self.m2_core_service = m2_core_service

    async def cotizar_proceso(
        self,
        area_solicitada: float,
        tarifa_m2_id: str,
    ) -> CotizacionM2Result:
        """
        Validates area and executes quote calculation.
        """
        if area_solicitada <= 0:
            raise HttpError(400, "area_solicitada must be greater than 0")

        calculo_func = sync_to_async(
            self.m2_core_service.calcular_cotizacion_m2,
            thread_sensitive=True
        )
        response = await calculo_func(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
        )

        return response
