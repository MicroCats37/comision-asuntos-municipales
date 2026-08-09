"""
HTTP Controller for Taludes (PorcentajeObra).

Endpoints:
- GET  /api/liquidaciones/taludes/tarifas/vigentes
- POST /api/liquidaciones/taludes/cotizar
- POST /api/liquidaciones/taludes/nueva-liquidacion/primera-revision

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.core.auth.auth_core_service import (
    AuthCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_taludes_orchestrator import (
    LiquidacionTaludesOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_taludes_presenter import (
    LiquidacionTaludesPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_taludes_schemas import (
    LiquidacionTaludesInput,
    LiquidacionTaludesOutput,
    LiquidacionTaludesCotizarInput,
    LiquidacionTaludesCotizarOutput,
)


@api_controller("/liquidaciones/taludes", tags=["Taludes"], permissions=[AllowAny])
class LiquidacionTaludesController:
    """
    Unified controller for Taludes (PorcentajeObra) endpoints.
    """

    @inject
    def __init__(
        self,
        taludes_orchestrator: LiquidacionTaludesOrchestrator,
        presenter: LiquidacionTaludesPresenter,
        auth_core_service: AuthCoreService,
    ):
        self.orchestrator = taludes_orchestrator
        self.presenter = presenter
        self.auth_core_service = auth_core_service

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[dict]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tarifas and derecho for Taludes.
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
        response={200: ApiResponse[LiquidacionTaludesOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionTaludesInput):
        """
        Crea la Liquidación de Taludes integrando General y PorcentajeObra.
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
        response={200: ApiResponse[LiquidacionTaludesCotizarOutput]},
        auth=None,
    )
    def cotizar(self, payload: LiquidacionTaludesCotizarInput):
        """
        Calculates a quote for Taludes liquidacion WITHOUT persisting.
        """
        le = payload.liquidacion_especifica
        valor_declarado = le.datos.valor_declarado

        domain_result = self.orchestrator.cotizar_proceso(
            valor_declarado=valor_declarado,
            tarifas_input=le.tarifas,
        )

        presented = self.presenter.present_cotizacion(domain_result)
        return success_response(presented)
