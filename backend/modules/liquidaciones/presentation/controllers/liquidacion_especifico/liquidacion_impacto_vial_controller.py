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

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[dict]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tarifas and derecho for Impacto Vial.
        """
        tarifas = self.orchestrator.obtener_tarifas_vigentes_proceso()
        presented = self.presenter.present_tarifas_vigentes(tarifas)
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
        return success_response(result)

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
