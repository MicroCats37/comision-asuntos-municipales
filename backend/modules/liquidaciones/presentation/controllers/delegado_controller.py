"""
DelegadoController — Thin HTTP controller for Delegado endpoints.

NO business logic. Only: parse input, call orchestrator, map via presenter.
Follows the 3 controller patterns from PLAN_REFACTORIZACION.md.
"""
import uuid
from typing import Optional
from ninja import Query
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
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    DelegadoCandidatasOut,
    DelegadoTiposLiquidacionOut,
    DelegadoOperatividadesVigentesOut,
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
    def list_delegados(
        self,
        page: int = 1,
        page_size: int = 10,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        capitulo_id: Optional[uuid.UUID] = None,
        especialidad_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
    ):
        """
        GET /delegados/?cip=&municipalidad_id=&capitulo_id=&especialidad_id=&estado=
        - List all delegados paginated, con municipalidades y estado.
        - estado: vigente | sin_vigencia | sin_asignaciones
        """
        domain_result = self.orchestrator.list_delegados_proceso(
            page=page,
            page_size=page_size,
            cip=cip,
            municipalidad_id=municipalidad_id,
            capitulo_id=capitulo_id,
            especialidad_id=especialidad_id,
            estado=estado,
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
        # Pass raw params to orchestrator — no parsing in controller
        domain_result = self.orchestrator.list_delegados_por_municipalidad_proceso(
            municipalidad_id=municipalidad_id,
            vigente=vigente,
            page=page,
            page_size=page_size,
        )
        return success_response(self.presenter.present_delegados_por_municipalidad(domain_result))

    @route.get(
        "/candidatas",
        response={200: ApiResponse[DelegadoCandidatasOut]},
        auth=None,
    )
    def list_candidatas(
        self,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        tipo_liquidacion_id: Optional[uuid.UUID] = None,
        tipo_delegado: Optional[str] = None,
        delegado_operacion_id: Optional[uuid.UUID] = Query(
            default=None,
            description="DelegadoOperacion ID (from SmartField). If provided, cip/municipalidad/tipo_liquidacion/tipo_delegado are ignored.",
        ),
        fecha_inicio: Optional[str] = Query(default=None, description="Filter by fecha_registro >= date (YYYY-MM-DD)"),
        fecha_fin: Optional[str] = Query(default=None, description="Filter by fecha_registro <= date (YYYY-MM-DD)"),
    ):
        """
        GET /delegados/candidatas?delegado_operacion_id=...
        OR GET /delegados/candidatas?cip=...&municipalidad_id=...&tipo_liquidacion_id=...&tipo_delegado=...

        Get candidate liquidaciones for a resolved DelegadoOperacion (for RH Mensual).

        Path 1 — SmartField (delegado_operacion_id provided):
          - Resolve DelegadoOperacion directly by ID.
          - Validate it belongs to cip (if cip provided).
          - Validate it is vigente (current active).
          - Use operation's municipalidad/especialidad/tipo to filter candidatas.
          - Does NOT require municipalidad_id, tipo_liquidacion_id, or tipo_delegado.

        Path 2 — Filter-based (delegado_operacion_id NOT provided):
          - Resolves exactly ONE active DelegadoOperacion matching:
            cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + current vigency.
          - Returns 404 if no operation found. Returns 409 if multiple operations match.

        Once resolved, uses the operation's especialidad_revision_id internally to filter candidatas.

        Filtros de fecha (opcionales):
        - fecha_inicio: fecha de registro >= fecha_inicio (inclusive)
        - fecha_fin: fecha de registro <= fecha_fin (inclusive)
        - Si fecha_inicio > fecha_fin: retorna 422 con error.
        """
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            from ninja.errors import HttpError
            raise HttpError(422, "fecha_inicio no puede ser mayor que fecha_fin")

        domain_result = self.orchestrator.list_candidatas_delegado_proceso(
            cip=cip,
            municipalidad_id=municipalidad_id,
            tipo_liquidacion_id=tipo_liquidacion_id,
            tipo_delegado=tipo_delegado,
            delegado_operacion_id=delegado_operacion_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        return success_response(self.presenter.present_candidatas(domain_result))

    @route.get(
        "/tipos-liquidacion",
        response={200: ApiResponse[DelegadoTiposLiquidacionOut]},
        auth=None,
    )
    def list_tipos_liquidacion(self):
        """
        GET /delegados/tipos-liquidacion — Get all TipoLiquidacion for select dropdowns.
        Returns { tipos: [{ id, codigo, nombre }] }.
        """
        tipos = self.orchestrator.list_tipos_liquidacion_proceso()
        return success_response(self.presenter.present_tipos_liquidacion(tipos))

    @route.get(
        "/operatividades-vigentes",
        response={200: ApiResponse[DelegadoOperatividadesVigentesOut]},
        auth=None,
    )
    def list_operatividades_vigentes(self, cip: str):
        """
        GET /delegados/operatividades-vigentes?cip=... — Get all active DelegadoOperacion
        for a delegado identified by CIP.

        Returns all vigente operations with their municipalidad, tipo_liquidacion,
        especialidad, tipo (TITULAR/ALTERNO), and vigencia period info.

        Raises 404 if no delegado found with that CIP.
        """
        domain_result = self.orchestrator.list_operatividades_vigentes_delegado_proceso(
            cip=cip,
        )
        return success_response(
            self.presenter.present_operatividades_vigentes(domain_result)
        )
