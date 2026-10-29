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
from typing import Optional
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
    LiquidacionEdificacionesCotizarEdicionIn,
    LiquidacionEdificacionesNuevaRevisionInput,
    LiquidacionEdificacionesRelacionadaInput,
    LiquidacionEdificacionesPatchIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.po_edge_schemas import (
    POEdgeIn,
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
    )
    def get_tarifas_vigentes(
        self,
        fecha: Optional[date] = Query(default=None, description="Optional date to get vigentes at that date (YYYY-MM-DD). If omitted, returns current vigentes."),
    ):
        """
        Get the currently active (or historical at fecha) tarifas and derecho for Edificaciones.

        - Sin fecha: devuelve tarifas vigentes a HOY (comportamiento original).
        - Con fecha: devuelve tarifas vigentes en esa fecha (para modo edición con fecha_registro).
        """
        tarifas, especialidades_disponibles = self.orchestrator.obtener_tarifas_vigentes_proceso(fecha=fecha)
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
        direccion: str = Query(default=None, description="Filter by proyecto direccion (icontains)"),
        documento: str = Query(default=None, description="Filter by entidad numero_documento (icontains)"),
        expediente: str = Query(default=None, description="Filter by expediente (icontains)"),
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
            direccion=direccion,
            documento=documento,
            expediente=expediente,
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
    )
    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single Edificacion liquidacion by ID.
        """
        liquidacion = self.orchestrator.obtener_liquidacion(liquidacion_id)
        result = self.presenter.present_detalle(liquidacion)
        return success_response(result)

    @route.patch(
        "/{uuid:liquidacion_id}",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def actualizar_calculo(
        self,
        liquidacion_id: uuid.UUID,
        data: LiquidacionEdificacionesPatchIn,
    ):
        """
        PATCH recalculation of PO calculation inputs.

        Supports two input formats:
        1. Wrapper (recommended): { liquidacion_general: {...}, liquidacion_tipo: {...} }
        2. Flat (legacy): { valor_declarado: ..., tarifas: [...] }

        Both general and tipo fields can be updated in one call.
        `liquidacion_tipo.estrategia_cotizacion` transiciona la estrategia de
        cotización (si se omite, se conserva la persistida).
        Solo editable cuando estado == PENDIENTE. PAGADA bloquea toda la edición.
        """
        # Extract wrapper data if present
        liquidacion_general = data.liquidacion_general.model_dump(exclude_none=True) if data.liquidacion_general else None
        liquidacion_tipo = data.liquidacion_tipo.model_dump(exclude_none=True) if data.liquidacion_tipo else None

        result = self.orchestrator.recalcular_po(
            liquidacion_id=liquidacion_id,
            valor_declarado=data.valor_declarado,
            tarifas=data.tarifas,
            liquidacion_general=liquidacion_general,
            liquidacion_tipo=liquidacion_tipo,
        )
        output = self.presenter.present_detalle(result)
        return success_response(output, message="Cálculo de edificación actualizado correctamente.")

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
        return success_response(result, message="Edificación creada correctamente.")

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
        return success_response(result, message="Nueva revisión de edificación creada correctamente.")

    @route.post(
        "/relacionada",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def crear_relacionada(self, request, payload: LiquidacionEdificacionesRelacionadaInput):
        """
        Crea una liquidación relacionada a una existente con numero_revision=1.

        A diferencia de /nueva-revision que crea revisiones 3 o 5, esta endpoint
        crea una nueva liquidación con revision 1 que está relacionada a la
        liquidación previa vía Grupo/Miembro.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_relacionada_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
            liquidacion_previa_id=payload.liquidacion_previa_id,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación relacionada de edificación creada correctamente.")

    @route.post(
        "/cotizar",
        response={200: ApiResponse[LiquidacionEdificacionesCotizarOutput]},
    )
    def cotizar(self, payload: LiquidacionEdificacionesCotizarInput):
        """
        Calculates a quote for Edificaciones liquidacion WITHOUT persisting.

        The strategy (union discriminado) travels inside liquidacion_especifica:
        the orchestrator resolves the context and the unique PO engine produces
        the same figures that the first-revision flow will persist.
        """
        domain_result = self.orchestrator.cotizar_proceso(
            estrategia_in=payload.liquidacion_especifica,
        )

        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)

    @route.post(
        "/{uuid:liquidacion_id}/cotizar-edicion",
        response={200: ApiResponse[LiquidacionEdificacionesCotizarOutput]},
    )
    def cotizar_edicion(self, liquidacion_id: uuid.UUID, payload: LiquidacionEdificacionesCotizarEdicionIn):
        """
        Read-only quote preview for editing an existing Edificaciones liquidacion.

        Uses historical financial values (IGV, UIT, tarifas) from the
        existing liquidacion's fecha_registro. Does NOT persist any changes.

        The route IS the type discriminator — no motor or tipo_liquidacion in body.
        `liquidacion_tipo` es la union discriminado de estrategias de Edificaciones:
        el preview usa el MISMO motor que el guardado.
        """
        domain_result = self.orchestrator.cotizar_edicion_proceso(
            liquidacion_id=liquidacion_id,
            payload_in=payload,
        )
        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)

    @route.post(
        "/edge",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def crear_edge(self, request, payload: POEdgeIn):
        """
        Create an edge (manual) PO liquidacion for Edificaciones.

        No tarifas, no valor_declarado — the backend distributes subtotal_manual
        equally among vigente specialties and calculates IGV/total.
        modo_calculo is set to MANUAL.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_edge_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Edificación (edge) creada correctamente.")
