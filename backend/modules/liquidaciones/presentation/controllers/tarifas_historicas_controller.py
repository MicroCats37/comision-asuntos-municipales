"""
TarifasHistoricasController — Controller for historical tariff and derecho endpoints.

ZERO business logic. Only parses input, delegates to orchestrator, maps via presenter.
"""
from datetime import date
from typing import Optional, Union, List
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
    # General endpoint schemas
    TarifaPorcentajeItemSchema,
    TarifaM2ItemSchema,
    TarifaVisitasItemSchema,
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
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        page: int = 1,
        page_size: int = 10,
    ):
        """
        Get historical tariff matrix for a tipo_liquidacion within a date range.

        - Query params: fecha_desde, fecha_hasta, page, page_size
        - If both dates are omitted: returns only currently vigentes tariffs
        - Groups tariffs by periodo_inicio/fin
        - For PorcentajeObra types: includes tarifas per especialidad
        - For M2 types: includes single tarifa_m2 detail
        - For Visitas types: includes multiple categorias
        """
        # Ninja already parses Optional[date] query params; pass directly
        # (orchestrator handles None -> vigentes at reference date/today)
        resultados, total = self.tarifas_orchestrator.obtener_tarifas_historicas_proceso(
            tipo=tipo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
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
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ):
        """
        Get historical derechos (PORCENTAJE or METRO_CUADRADO) within a date range.

        - Query params: tipo (PORCENTAJE|METRO_CUADRADO), fecha_desde, fecha_hasta
        - If both dates are omitted: returns only currently vigentes derechos
        - Returns list of derechos with their vigencia periods
        """
        # Ninja already parses Optional[date] query params; pass directly
        # (orchestrator handles None -> vigentes at reference date/today)
        resultados = self.derechos_orchestrator.obtener_derechos_historicos_proceso(
            tipo=tipo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        result = self.derechos_presenter.present_derechos_historicos(resultados)
        return success_response(result)

    @route.get(
        "/tarifas",
        response={200: ApiResponse[List[Union[
            TarifaPorcentajeItemSchema,
            TarifaM2ItemSchema,
            TarifaVisitasItemSchema,
        ]]]},
        auth=None,
    )
    def get_tarifas_generales(
        self,
        vigentes: bool = False,
        fecha_ref: Optional[date] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ):
        """
        Get tariff matrix for ALL tipo_liquidacion (general tarifario view).

        Query params:
        - vigentes (default False): if True, return vigentes at fecha_ref (or today).
          if False, return all tariffs, optionally filtered by fecha_desde/fecha_hasta.
        - fecha_ref: reference date for vigentes filter (default: today).
        - fecha_desde, fecha_hasta: date range for historical queries (used when vigentes=False).

        Response is an unpaginated array of discriminated tariff items.
        Each item has tipo_tarifa discriminator and only its relevant detail key.
        """
        resultados = self.tarifas_orchestrator.obtener_tarifas_generales_proceso(
            vigentes=vigentes,
            fecha_ref=fecha_ref,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        items = self.tarifas_presenter.present_tarifas_generales(resultados)
        return success_response(items)
