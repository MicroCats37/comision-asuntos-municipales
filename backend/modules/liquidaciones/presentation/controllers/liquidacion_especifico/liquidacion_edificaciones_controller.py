"""
HTTP Controller for Edificaciones (PorcentajeObra).

Endpoints:
- GET  /api/liquidaciones/edificaciones/tarifas/vigentes
- POST /api/liquidaciones/edificaciones/cotizar
- POST /api/liquidaciones/edificaciones/nueva-liquidacion/primera-revision

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
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
        tarifas = self.orchestrator.obtener_tarifas_vigentes_proceso()
        return success_response({
            "tarifas": [
                {
                    "id": str(t.id),
                    "especialidad": t.especialidad.nombre,
                    "porcentaje_liquidacion": float(t.porcentaje_liquidacion),
                }
                for t in tarifas
            ],
        })

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
        payload_tarifas_ids = [
            str(t.tarifa_porcentaje_obra_id)
            for t in le.tarifas
        ]

        domain_result = self.orchestrator.cotizar_proceso(
            valor_declarado=valor_declarado,
            payload_tarifas_ids=payload_tarifas_ids,
        )

        return success_response(domain_result)
