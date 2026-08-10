"""
TarifasHistoricasController — Controller for historical tariff and derecho endpoints.

ZERO business logic. Only parses input, delegates to orchestrator, maps via presenter.
"""
from datetime import date
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.orchestrators.tarifas_historicas_orchestrator import (
    TarifasHistoricasOrchestrator,
)
from modules.liquidaciones.domain.services.orchestrators.derechos_historicos_orchestrator import (
    DerechosHistoricosOrchestrator,
)
from modules.liquidaciones.presentation.schemas.tarifas_historicas_schemas import (
    TarifaHistoricaPeriodoSchema,
    DerechosHistoricosResponseSchema,
)
from modules.liquidaciones.presentation.presenters.tarifas_historicas_presenter import (
    TarifasHistoricasPresenter,
    DerechosHistoricosPresenter,
)


@api_controller("/liquidaciones", tags=["Tarifas y Derechos Históricos"], permissions=[AllowAny])
class TarifasHistoricasController:
    """
    Controller for historical tariff and derecho queries.
    """

    @inject
    def __init__(
        self,
        tarifas_orchestrator: TarifasHistoricasOrchestrator,
        derechos_orchestrator: DerechosHistoricosOrchestrator,
        tarifas_presenter: TarifasHistoricasPresenter,
        derechos_presenter: DerechosHistoricosPresenter,
    ):
        self.tarifas_orchestrator = tarifas_orchestrator
        self.derechos_orchestrator = derechos_orchestrator
        self.tarifas_presenter = tarifas_presenter
        self.derechos_presenter = derechos_presenter

    @route.get(
        "/{tipo}/tarifas/historicas",
        response={200: ApiResponse[PaginatedData[TarifaHistoricaPeriodoSchema]]},
        auth=None,
    )
    def get_tarifas_historicas(
        self,
        tipo: str,
        fecha_desde: str,
        fecha_hasta: str,
        page: int = 1,
        page_size: int = 10,
    ):
        """
        Get historical tariff matrix for a tipo_liquidacion within a date range.
        
        - Query params: fecha_desde, fecha_hasta, page, page_size
        - Groups tariffs by periodo_inicio/fin
        - For PorcentajeObra types: includes tarifas per especialidad
        - For M2 types: includes single tarifa_m2 detail
        - For Visitas types: includes multiple categorias
        """
        # Parse dates
        desde = date.fromisoformat(fecha_desde)
        hasta = date.fromisoformat(fecha_hasta)

        resultados, total = self.tarifas_orchestrator.obtener_tarifas_historicas_proceso(
            tipo=tipo,
            fecha_desde=desde,
            fecha_hasta=hasta,
            page=page,
            page_size=page_size,
        )

        result = self.tarifas_presenter.present_tarifas_historicas(
            resultados=resultados,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.get(
        "/derechos/historicos",
        response={200: ApiResponse[DerechosHistoricosResponseSchema]},
        auth=None,
    )
    def get_derechos_historicos(
        self,
        tipo: str,
        fecha_desde: str,
        fecha_hasta: str,
    ):
        """
        Get historical derechos (PORCENTAJE or METRO_CUADRADO) within a date range.
        
        - Query params: tipo (PORCENTAJE|METRO_CUADRADO), fecha_desde, fecha_hasta
        - Returns list of derechos with their vigencia periods
        """
        # Parse dates
        desde = date.fromisoformat(fecha_desde)
        hasta = date.fromisoformat(fecha_hasta)

        resultados = self.derechos_orchestrator.obtener_derechos_historicos_proceso(
            tipo=tipo,
            fecha_desde=desde,
            fecha_hasta=hasta,
        )

        result = self.derechos_presenter.present_derechos_historicos(resultados)
        return success_response(result)