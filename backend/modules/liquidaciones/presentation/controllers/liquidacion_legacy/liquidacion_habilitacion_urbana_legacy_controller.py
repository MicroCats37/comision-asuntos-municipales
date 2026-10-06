"""
HTTP Controller for Habilitación Urbana (PorMetroCuadrado) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_habilitacion_urbana_legacy_orchestrator import (
    LiquidacionHabilitacionUrbanaLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_habilitacion_urbana_presenter import (
    LiquidacionHabilitacionUrbanaPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_habilitacion_urbana_legacy_schemas import (
    LiquidacionHabilitacionUrbanaLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaOutput,
)


@api_controller("/liquidaciones/habilitacion-urbana", tags=["Habilitación Urbana Legacy"], permissions=[AllowAny])
class LiquidacionHabilitacionUrbanaLegacyController:
    """
    Legacy controller for Habilitación Urbana (PorMetroCuadrado) with historical fecha_registro (supports any numero_revision).
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionHabilitacionUrbanaLegacyOrchestrator,
        presenter: LiquidacionHabilitacionUrbanaPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion",
        response={200: ApiResponse[LiquidacionHabilitacionUrbanaOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionHabilitacionUrbanaLegacyIn):
        """
        Crea la Habilitación Urbana con tarifas históricas basadas en fecha_registro.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación legacy de habilitación urbana creada correctamente.")
