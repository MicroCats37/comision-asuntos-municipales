"""
DelegadoController — Thin HTTP controller for Delegado endpoints.

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
from modules.liquidaciones.domain.services.orchestrators.delegado_orchestrator import (
    DelegadoOrchestrator,
)
from modules.liquidaciones.presentation.presenters.delegado_presenter import (
    DelegadoPresenter,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_schemas import (
    DelegadoOut,
    DelegadoListOut,
    DelegadoMunicipalidadesOut,
    DelegadoForMunicipalidadOut,
    DelegadosPorMunicipalidadOut,
)


@api_controller("/delegados", tags=["Delegados"], permissions=[AllowAny])
class DelegadoController:
    """
    Controller for Delegado endpoints.
    """

    @inject
    def __init__(
        self,
        orchestrator: DelegadoOrchestrator,
        presenter: DelegadoPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.get(
        "/",
        response={200: ApiResponse[DelegadoListOut]},
        auth=None,
    )
    def list_delegados(self, page: int = 1, page_size: int = 10):
        """
        GET /delegados/ — List all delegados paginated.
        """
        domain_result = self.orchestrator.list_delegados_proceso(
            page=page,
            page_size=page_size,
        )
        return success_response(self.presenter.present_list(domain_result))

    @route.get(
        "/{delegado_id}/municipalidades",
        response={200: ApiResponse[DelegadoMunicipalidadesOut]},
        auth=None,
    )
    def obtener_municipalidades(self, delegado_id: uuid.UUID):
        """
        GET /delegados/{delegado_id}/municipalidades — Get a delegado's municipalidad
        assignments with vigencia status.
        """
        domain_result = self.orchestrator.obtener_municipalidades_proceso(
            delegado_id=delegado_id,
        )
        return success_response(self.presenter.present_municipalidades(domain_result))

    @route.get(
        "/municipalidad/{municipalidad_id}",
        response={200: ApiResponse[DelegadosPorMunicipalidadOut]},
        auth=None,
    )
    def list_delegados_por_municipalidad(
        self,
        municipalidad_id: uuid.UUID,
        vigente: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ):
        """
        GET /delegados/municipalidad/{id}?vigente=true — Get all delegados for a municipalidad,
        with optional vigencia filter (periodo_inicio <= today AND
        (periodo_fin IS NULL OR periodo_fin >= today)).
        """
        # Parse vigentes string to bool - Ninja's bool parser doesn't handle "false" properly
        vigente_bool: Optional[bool] = None
        if vigente is not None:
            vigente_bool = vigente.lower() == "true"

        domain_result = self.orchestrator.list_delegados_por_municipalidad_proceso(
            municipalidad_id=municipalidad_id,
            vigente=vigente_bool,
            page=page,
            page_size=page_size,
        )
        return success_response(self.presenter.present_delegados_por_municipalidad(domain_result))
