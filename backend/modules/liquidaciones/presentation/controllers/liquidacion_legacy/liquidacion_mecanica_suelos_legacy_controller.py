"""
HTTP Controller for Mecánica de Suelos (PorMetroCuadrado) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_mecanica_suelos_legacy_orchestrator import (
    LiquidacionMecanicaSuelosLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_mecanica_suelos_presenter import (
    LiquidacionMecanicaSuelosPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_mecanica_suelos_legacy_schemas import (
    LiquidacionMecanicaSuelosLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosOutput,
)


@api_controller("/liquidaciones/mecanica-suelos", tags=["Mecánica de Suelos Legacy"], permissions=[AllowAny])
class LiquidacionMecanicaSuelosLegacyController:
    """
    Legacy controller for Mecánica de Suelos (PorMetroCuadrado) with historical fecha_registro (supports any numero_revision).
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionMecanicaSuelosLegacyOrchestrator,
        presenter: LiquidacionMecanicaSuelosPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionMecanicaSuelosLegacyIn):
        """
        Crea la Mecánica de Suelos con tarifas históricas basadas en fecha_registro.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación legacy de mecánica de suelos creada correctamente.")
