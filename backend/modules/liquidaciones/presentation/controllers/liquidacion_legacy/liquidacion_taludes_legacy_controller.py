"""
HTTP Controller for Taludes (PorcentajeObra) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/taludes/legacy/nueva-liquidacion

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_taludes_legacy_orchestrator import (
    LiquidacionTaludesLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_taludes_presenter import (
    LiquidacionTaludesPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_taludes_legacy_schemas import (
    LiquidacionTaludesLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_taludes_schemas import (
    LiquidacionTaludesOutput,
)


@api_controller("/liquidaciones/taludes", tags=["Taludes Legacy"], permissions=[AllowAny])
class LiquidacionTaludesLegacyController:
    """
    Legacy controller for Taludes (PorcentajeObra) with historical fecha_registro (supports any numero_revision).
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionTaludesLegacyOrchestrator,
        presenter: LiquidacionTaludesPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion",
        response={200: ApiResponse[LiquidacionTaludesOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionTaludesLegacyIn):
        """
        Crea el Talud con tarifas históricas basadas en fecha_registro.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)
