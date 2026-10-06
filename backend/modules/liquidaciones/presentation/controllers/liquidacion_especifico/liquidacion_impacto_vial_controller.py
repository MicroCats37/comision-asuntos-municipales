"""
HTTP Controller for Impacto Vial (PorcentajeObra).

Endpoints:
- GET  /api/liquidaciones/impacto-vial/
- GET  /api/liquidaciones/impacto-vial/tarifas/vigentes
- POST /api/liquidaciones/impacto-vial/cotizar
- POST /api/liquidaciones/impacto-vial/nueva-liquidacion/primera-revision
- GET  /api/liquidaciones/impacto-vial/{liquidacion_id}

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
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_impacto_vial_orchestrator import (
    LiquidacionImpactoVialOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_impacto_vial_presenter import (
    LiquidacionImpactoVialPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_impacto_vial_schemas import (
    LiquidacionImpactoVialInput,
    LiquidacionImpactoVialOutput,
    LiquidacionImpactoVialCotizarInput,
    LiquidacionImpactoVialCotizarOutput,
    LiquidacionImpactoVialRelacionadaInput,
    LiquidacionImpactoVialNuevaRevisionInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_po_schemas import (
    LiquidacionPatchPOIn,
    LiquidacionPatchPOWrapperIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
    CotizarEdicionPOWrapperIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.po_edge_schemas import (
    POEdgeIn,
)


@api_controller("/liquidaciones/impacto-vial", tags=["Impacto Vial"], permissions=[AllowAny])
class LiquidacionImpactoVialController:
    """
    Unified controller for Impacto Vial (PorcentajeObra) endpoints.
    """

    @inject
    def __init__(
        self,
        impacto_vial_orchestrator: LiquidacionImpactoVialOrchestrator,
        presenter: LiquidacionImpactoVialPresenter,
        auth_core_service: AuthCoreService,
    ):
        self.orchestrator = impacto_vial_orchestrator
        self.presenter = presenter
        self.auth_core_service = auth_core_service

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionImpactoVialOutput]]},
    )
    def listar_liquidaciones(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        entidad_id: uuid.UUID = Query(default=None, description="Filter by municipalidad ID"),
        propietario: str = Query(default=None, description="Filter by propietario name (icontains)"),
        fecha_desde: date = Query(default=None, description="Filter by fecha_registro >= date"),
        fecha_hasta: date = Query(default=None, description="Filter by fecha_registro <= date"),
        numero: int = Query(default=None, description="Filter by impacto_vial numero (exact)"),
        razon_social: str = Query(default=None, description="Filter by entidad razon_social (icontains)"),
        creado_por: str = Query(default=None, description="Filter by usuario_creador username (icontains)"),
        numero_revisiones: int = Query(default=None, description="Filter by numero_revision (exact)"),
        direccion: str = Query(default=None, description="Filter by proyecto direccion (icontains)"),
    ):
        """
        Returns paginated list of Impacto Vial liquidaciones with optional filters.
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
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
        auth=None,
    )
    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single Impacto Vial liquidacion by UUID.
        """
        liquidacion = self.orchestrator.obtener_liquidacion(liquidacion_id)
        result = self.presenter.present_detalle(liquidacion)
        return success_response(result)

    @route.patch(
        "/{uuid:liquidacion_id}",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def actualizar_calculo(
        self,
        liquidacion_id: uuid.UUID,
        data: LiquidacionPatchPOWrapperIn,
    ):
        """
        PATCH recalculation of PO calculation inputs.

        Supports two input formats:
        1. Wrapper (recommended): { liquidacion_general: {...}, liquidacion_tipo: {...} }
        2. Flat (legacy): { valor_declarado: ..., tarifas: [...] }

        Both general and tipo fields can be updated in one call.
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
        return success_response(output, message="Cálculo de impacto vial actualizado correctamente.")

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[dict]},
        auth=None,
    )
    def get_tarifas_vigentes(
        self,
        fecha: Optional[date] = Query(default=None, description="Optional date to get vigentes at that date (YYYY-MM-DD). If omitted, returns current vigentes."),
    ):
        """
        Get the currently active (or historical at fecha) tarifas and derecho for Impacto Vial.
        """
        tarifas, especialidades_disponibles = self.orchestrator.obtener_tarifas_vigentes_proceso(fecha=fecha)
        presented = self.presenter.present_tarifas_vigentes(tarifas, especialidades_disponibles)
        return success_response(presented)

    @route.post(
        "/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionImpactoVialInput):
        """
        Crea la Liquidación de Impacto Vial integrando General y PorcentajeObra.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación de impacto vial creada correctamente.")

    @route.post(
        "/nueva-revision",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def crear_nueva_revision(self, request, payload: LiquidacionImpactoVialNuevaRevisionInput):
        """
        Crea una nueva revisión (3 o 5) para una liquidación de Impacto Vial existente.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.orchestrator.crear_nueva_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
            liquidacion_previa_id=payload.liquidacion_previa_id,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Nueva revisión de impacto vial creada correctamente.")

    @route.post(
        "/relacionada",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def crear_relacionada(self, request, payload: LiquidacionImpactoVialRelacionadaInput):
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
        return success_response(result, message="Liquidación relacionada de impacto vial creada correctamente.")

    @route.post(
        "/cotizar",
        response={200: ApiResponse[LiquidacionImpactoVialCotizarOutput]},
        auth=None,
    )
    def cotizar(self, payload: LiquidacionImpactoVialCotizarInput):
        """
        Calculates a quote for Impacto Vial liquidacion WITHOUT persisting.
        """
        le = payload.liquidacion_especifica
        valor_declarado = le.datos.valor_declarado

        domain_result = self.orchestrator.cotizar_proceso(
            valor_declarado=valor_declarado,
            tarifas_input=le.tarifas,
        )

        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)

    @route.post(
        "/{uuid:liquidacion_id}/cotizar-edicion",
        response={200: ApiResponse[LiquidacionImpactoVialCotizarOutput]},
    )
    def cotizar_edicion(self, liquidacion_id: uuid.UUID, payload: CotizarEdicionPOWrapperIn):
        """
        Read-only quote preview for editing an existing Impacto Vial liquidacion.

        Uses historical financial values from the existing liquidacion's fecha_registro.
        Does NOT persist any changes.
        """
        domain_result = self.orchestrator.cotizar_edicion_proceso(
            liquidacion_id=liquidacion_id,
            payload_in=payload,
        )
        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)

    @route.post(
        "/edge",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def crear_edge(self, request, payload: POEdgeIn):
        """
        Create an edge (manual) PO liquidacion for Impacto Vial.

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
        return success_response(result, message="Liquidación de impacto vial (edge) creada correctamente.")
