"""
LiquidacionInspeccionObraController — Single unified HTTP controller for Inspeccion Obra.
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
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraInput,
    LiquidacionInspeccionObraOutput,
    LiquidacionInspeccionObraNuevaRevisionInput,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_inspeccion_obra_orchestrator import (
    LiquidacionInspeccionObraOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_inspeccion_obra_presenter import (
    LiquidacionInspeccionObraPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_tipo.liquidacion_por_categoria_visitas_presenter import (
    LiquidacionPorCategoriaVisitasPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    TarifasVigentesPorCategoriaVisitasOutputSchema,
    CotizarPorCategoriaVisitasInputSchema,
    CotizarPorCategoriaVisitasOutputSchema,
)

@api_controller("/liquidaciones/inspeccion-obra", tags=["Inspección de Obra"], permissions=[AllowAny])
class LiquidacionInspeccionObraController:
    """
    Unified controller for Inspeccion Obra endpoints.
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionInspeccionObraOrchestrator,
        visitas_presenter: LiquidacionPorCategoriaVisitasPresenter,
        presenter: LiquidacionInspeccionObraPresenter,
        auth_core_service: AuthCoreService,
    ):
        self.orchestrator = orchestrator
        self.visitas_presenter = visitas_presenter
        self.presenter = presenter
        self.auth_core_service = auth_core_service

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[TarifasVigentesPorCategoriaVisitasOutputSchema]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tariffs for Inspeccion Obra (Visitas).
        Delegates fetching and validation to the Orchestrator.
        """
        tarifas, uit_vigente = self.orchestrator.obtener_tarifas_vigentes_proceso()
        result = self.visitas_presenter.present_tarifas_vigentes(tarifas=tarifas, uit_vigente=uit_vigente)
        return success_response(result)

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionInspeccionObraOutput]]},
        auth=None,
    )
    def list_liquidaciones(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        entidad_id: uuid.UUID = Query(default=None, description="Filter by municipalidad ID"),
        propietario: str = Query(default=None, description="Filter by propietario name (icontains)"),
        fecha_desde: date = Query(default=None, description="Filter by fecha_registro >= date"),
        fecha_hasta: date = Query(default=None, description="Filter by fecha_registro <= date"),
        numero: int = Query(default=None, description="Filter by inspeccion_obra numero (exact)"),
        razon_social: str = Query(default=None, description="Filter by entidad razon_social (icontains)"),
        creado_por: str = Query(default=None, description="Filter by usuario_creador username (icontains)"),
        numero_revisiones: int = Query(default=None, description="Filter by numero_revision (exact)"),
    ):
        """
        Returns a paginated list of Inspección de Obra liquidaciones with optional filters.
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
        response={200: ApiResponse[LiquidacionInspeccionObraOutput]},
        auth=None,
    )
    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single Inspección de Obra liquidacion by UUID.
        """
        lg = self.orchestrator.obtener_liquidacion(liquidacion_id)
        result = self.presenter.present_detalle(lg)
        return success_response(result)

    @route.post(
        "/cotizar",
        response={200: ApiResponse[CotizarPorCategoriaVisitasOutputSchema]},
        auth=None,
    )
    def cotizar(self, payload: CotizarPorCategoriaVisitasInputSchema):
        """
        Calculates a quote for Inspeccion Obra liquidacion.
        """
        le = payload.liquidacion_especifica
        cantidad_visitas = le.datos.cantidad_visitas
        categoria = le.datos.categoria
        tarifa_visitas_id = le.tarifa.tarifa_visitas_id

        result = self.orchestrator.cotizar_proceso(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_id=str(tarifa_visitas_id),
        )

        return success_response(self.visitas_presenter.present_cotizacion(result))

    @route.post(
        "/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionInspeccionObraOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionInspeccionObraInput):
        """
        Crea la Inspeccion de Obra integrando General y Visitas.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)

    @route.post(
        "/nueva-liquidacion/primera-revision-desde-previa",
        response={200: ApiResponse[LiquidacionInspeccionObraOutput]},
    )
    def crear_primera_revision_desde_previa(self, request, payload: LiquidacionInspeccionObraNuevaRevisionInput):
        """
        Crea una Inspección de Obra primera-revision heredando
        proyecto/municipalidad/entidad de una liquidación previa (Edificación o HU).
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_primera_revision_desde_previa_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)
