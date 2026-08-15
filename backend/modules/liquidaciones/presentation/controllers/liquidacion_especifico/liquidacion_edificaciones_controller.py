"""
HTTP Controller for Edificaciones (PorcentajeObra).

Endpoints:
- GET  /api/liquidaciones/edificaciones/tarifas/vigentes
- POST /api/liquidaciones/edificaciones/cotizar
- POST /api/liquidaciones/edificaciones/nueva-liquidacion/primera-revision
- GET  /api/liquidaciones/edificaciones/{liquidacion_id}

Thin controller — only delegates, no logic.
"""
import uuid
from datetime import date
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.core.auth.auth_core_service import (
    AuthCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_edificaciones_orchestrator import (
    LiquidacionEdificacionesOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_edificaciones_presenter import (
    LiquidacionEdificacionesPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesInput,
    LiquidacionEdificacionesOutput,
    LiquidacionEdificacionesCotizarInput,
    LiquidacionEdificacionesCotizarOutput,
    LiquidacionEdificacionesNuevaRevisionInput,
)


@api_controller("/liquidaciones/edificaciones", tags=["Edificaciones"], permissions=[AllowAny])
class LiquidacionEdificacionesController:
    """
    Unified controller for Edificaciones (PorcentajeObra) endpoints.
    """

    @inject
    def __init__(
        self,
        edificaciones_orchestrator: LiquidacionEdificacionesOrchestrator,
        presenter: LiquidacionEdificacionesPresenter,
        auth_core_service: AuthCoreService,
    ):
        self.orchestrator = edificaciones_orchestrator
        self.presenter = presenter
        self.auth_core_service = auth_core_service

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[dict]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tarifas and derecho for Edificaciones.
        """
        tarifas, especialidades_disponibles = self.orchestrator.obtener_tarifas_vigentes_proceso()
        presented = self.presenter.present_tarifas_vigentes(tarifas, especialidades_disponibles)
        return success_response(presented)

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionEdificacionesOutput]]},
    )
    def list_liquidaciones(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        entidad_id: uuid.UUID = Query(default=None, description="Filter by municipalidad ID"),
        propietario: str = Query(default=None, description="Filter by propietario name (icontains)"),
        fecha_desde: date = Query(default=None, description="Filter by fecha_registro >= date"),
        fecha_hasta: date = Query(default=None, description="Filter by fecha_registro <= date"),
        numero: int = Query(default=None, description="Filter by edificacion numero (exact)"),
        razon_social: str = Query(default=None, description="Filter by entidad razon_social (icontains)"),
        creado_por: str = Query(default=None, description="Filter by usuario_creador username (icontains)"),
        numero_revisiones: int = Query(default=None, description="Filter by numero_revision (exact)"),
    ):
        """
        Returns a paginated list of Edificaciones liquidaciones with optional filters.
        """
        liquidaciones, total = self.orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            municipalidad_id=entidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creado_por,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revisiones,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.get(
        "/{uuid:liquidacion_id}",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
        auth=None,
    )
    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single Edificacion liquidacion by ID.
        """
        liquidacion = self.orchestrator.obtener_liquidacion(liquidacion_id)
        result = self.presenter.present_detalle(liquidacion)
        return success_response(result)

    @route.post(
        "/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionEdificacionesInput):
        """
        Crea la Edificación integrando General y PorcentajeObra.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)

    @route.post(
        "/nueva-revision",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def crear_nueva_revision(self, request, payload: LiquidacionEdificacionesNuevaRevisionInput):
        """
        Crea una nueva revisión (3 o 5) para una Edificación existente.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_nueva_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
            liquidacion_previa_id=payload.liquidacion_previa_id,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)

    @route.get(
        "/ultima-revision",
        response={200: ApiResponse[PaginatedData[LiquidacionEdificacionesOutput]]},
    )
    def obtener_ultima_revision(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
        razon_social: str = Query(default=None, description="Filter by entidad razon_social (icontains)"),
        numero_documento: str = Query(default=None, description="Filter by entidad numero_documento"),
        fecha_desde: date = Query(default=None, description="Filter by fecha_registro >= date"),
        fecha_hasta: date = Query(default=None, description="Filter by fecha_registro <= date"),
    ):
        """
        Returns a paginated list of the latest revision per project for Edificaciones.
        Each item is the liquidacion with the highest numero_revision for a proyecto.
        """
        liquidaciones, total = self.orchestrator.obtener_ultima_revision_proceso(
            page=page,
            page_size=page_size,
            razon_social=razon_social,
            numero_documento=numero_documento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.post(
        "/cotizar",
        response={200: ApiResponse[LiquidacionEdificacionesCotizarOutput]},
        auth=None,
    )
    def cotizar(self, payload: LiquidacionEdificacionesCotizarInput):
        """
        Calculates a quote for Edificaciones liquidacion WITHOUT persisting.
        """
        le = payload.liquidacion_especifica
        valor_declarado = le.datos.valor_declarado

        domain_result = self.orchestrator.cotizar_proceso(
            valor_declarado=valor_declarado,
            tarifas_input=le.tarifas,
        )

        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)
