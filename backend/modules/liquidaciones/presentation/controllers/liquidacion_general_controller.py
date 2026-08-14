"""
LiquidacionGeneralController — Single unified HTTP controller for general liquidaciones.

NO business logic. Only parses input, calls orchestrator, maps via presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)


@api_controller("/liquidaciones/generales", tags=["Liquidaciones Generales"], permissions=[AllowAny])
class LiquidacionGeneralController:
    """
    Unified controller for general liquidaciones endpoints.
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionGeneralOrchestrator,
        presenter: LiquidacionGeneralPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionGeneralOutput]]},
    )
    def list_liquidaciones(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
        tipo: str = Query(default=None, description="Filter by tipo liquidacion codigo (e.g. EDIFICACION, HABILITACION_URBANA)"),
        documento: str = Query(default=None, description="Filter by proyecto entity numero documento (icontains)"),
        razon_social: str = Query(default=None, description="Filter by proyecto entidad razon social (icontains)"),
        propietario: str = Query(default=None, description="Filter by proyecto nombre propietario (icontains)"),
        expediente: str = Query(default=None, description="Filter by expediente numero (icontains)"),
        nombre_propietario: str = Query(default=None, description="Filter by proyecto nombre propietario — equivalent to 'propietario', both filter the same field"),
    ):
        """
        Returns a paginated list of all liquidaciones (any tipo) with optional filters.
        """
        liquidaciones, total = self.orchestrator.listar_liquidaciones_generales(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.get(
        "/ultimas-revisiones",
        response={200: ApiResponse[PaginatedData[LiquidacionGeneralOutput]]},
    )
    def list_ultimas_liquidaciones(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
        tipo: str = Query(default=None, description="Filter by tipo liquidacion codigo (e.g. EDIFICACION, HABILITACION_URBANA)"),
        documento: str = Query(default=None, description="Filter by proyecto entity numero documento (icontains)"),
        razon_social: str = Query(default=None, description="Filter by proyecto entidad razon social (icontains)"),
        propietario: str = Query(default=None, description="Filter by proyecto nombre propietario (icontains)"),
        expediente: str = Query(default=None, description="Filter by expediente numero (icontains)"),
        nombre_propietario: str = Query(default=None, description="Filter by proyecto nombre propietario — equivalent to 'propietario', both filter the same field"),
    ):
        """
        Returns a paginated list of the latest liquidaciones (one per proyecto+tipo_liquidacion pair)
        with optional filters.
        """
        liquidaciones, total = self.orchestrator.listar_ultimas_liquidaciones_generales(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)
