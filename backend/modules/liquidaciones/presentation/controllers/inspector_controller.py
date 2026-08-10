"""
InspectorController — Thin HTTP controller for Inspector endpoints.

NO business logic. Only: parse input, call orchestrator, map via presenter.
Follows the 3 controller patterns from PLAN_REFACTORIZACION.md.
"""
import uuid
from typing import Optional
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.orchestrators.inspector_orchestrator import (
    InspectorOrchestrator,
)
from modules.liquidaciones.presentation.presenters.inspector_presenter import (
    InspectorPresenter,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_schemas import (
    InspectorOut,
    InspectorListOut,
    InspectorDetailOut,
    InspectorVigenteOut,
    InspectorVigenteListOut,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


@api_controller("/inspectores", tags=["Inspectores"], permissions=[AllowAny])
class InspectorController:
    """
    Controller for Inspector endpoints.
    """

    @inject
    def __init__(
        self,
        orchestrator: InspectorOrchestrator,
        presenter: InspectorPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.get(
        "/",
        response={200: ApiResponse[InspectorListOut]},
        auth=None,
    )
    def list_inspectores(self, page: int = 1, page_size: int = 10):
        """
        GET /inspectores/ — List all inspectores paginated.
        """
        domain_result = self.orchestrator.list_inspectores_proceso(
            page=page,
            page_size=page_size,
        )
        return success_response(self.presenter.present_list(domain_result))

    @route.get(
        "/vigentes",
        response={200: ApiResponse[InspectorVigenteListOut]},
        auth=None,
    )
    def list_inspectores_vigentes(
        self,
        tipo_liquidacion: str,
        page: int = 1,
        page_size: int = 10,
    ):
        """
        GET /inspectores/vigentes?tipo_liquidacion=EDIFICACION|HABILITACION_URBANA
        — List all vigentes inspectores filtered by tipo_liquidacion.
        """
        domain_result = self.orchestrator.list_inspectores_vigentes_proceso(
            tipo_liquidacion=tipo_liquidacion,
            page=page,
            page_size=page_size,
        )
        return success_response(self.presenter.present_vigentes(domain_result))

    @route.get(
        "/{inspector_id}",
        response={200: ApiResponse[InspectorDetailOut]},
        auth=None,
    )
    def obtener_inspector(self, inspector_id: uuid.UUID):
        """
        GET /inspectores/{inspector_id} — Get a single inspector detail.
        """
        domain_result = self.orchestrator.obtener_inspector_proceso(
            inspector_id=inspector_id,
        )
        return success_response(self.presenter.present_detail(domain_result))
