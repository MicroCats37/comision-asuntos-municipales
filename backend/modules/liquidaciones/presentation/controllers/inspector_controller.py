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
    InspectoresSeleccionablesOut,
    LiquidacionInspectorAsignacionOut,
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


@api_controller(
    "/liquidaciones/inspectores",
    tags=["Inspectores de Liquidación"],
    permissions=[AllowAny],
)
class LiquidacionInspectorController:
    """
    Controller para inspectores relacionados a liquidaciones (form de creación IO).
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
        "/seleccionables",
        response={200: ApiResponse[InspectoresSeleccionablesOut]},
        auth=None,
    )
    def listar_inspectores_seleccionables(
        self,
        tipo_liquidacion: str = None,
        categoria: Optional[str] = None,
        q: Optional[str] = None,
    ):
        """
        GET /liquidaciones/inspectores/seleccionables?tipo_liquidacion=X
            &categoria=&q=

        Inspectores vigentes y elegibles para el form de creación de IO,
        sin paginación. Filtra por tipo (de la previa) y categoría, con
        búsqueda opcional por nombre/CIP (q).
        """
        if not tipo_liquidacion:
            from ninja.errors import HttpError
            raise HttpError(400, "El parámetro tipo_liquidacion es requerido")

        domain_result = self.orchestrator.listar_inspectores_seleccionables_proceso(
            tipo_liquidacion=tipo_liquidacion,
            categoria=categoria,
            q=q,
        )
        return success_response(self.presenter.present_seleccionables(domain_result))

    @route.get(
        "/inspectores-asignaciones",
        response={200: ApiResponse[PaginatedData[LiquidacionInspectorAsignacionOut]]},
        auth=None,
    )
    def listar_asignaciones_inspectores(
        self,
        page: int = 1,
        page_size: int = 10,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ):
        """
        GET /liquidaciones/inspectores/inspectores-asignaciones
            ?page=&page_size=&cip=&liquidacion_id=

        Lista paginada de asociaciones LiquidacionInspector (selector de
        Recibos de Honorarios de Inspectores). Cada item incluye
        liquidacion{}, inspector{} y especialidad_revision{} anidados.
        """
        results, total = self.orchestrator.listar_asignaciones_inspectores_proceso(
            page=page,
            page_size=page_size,
            cip=cip,
            liquidacion_id=liquidacion_id,
        )
        return success_response(
            self.presenter.present_asignaciones_inspectores_list(
                results, total, page, page_size
            )
        )
