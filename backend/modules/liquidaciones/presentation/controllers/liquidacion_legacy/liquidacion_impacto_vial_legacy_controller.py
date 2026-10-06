"""
HTTP Controller for Impacto Vial (PorcentajeObra) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/impacto-vial/legacy/nueva-liquidacion

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_impacto_vial_legacy_orchestrator import (
    LiquidacionImpactoVialLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_impacto_vial_presenter import (
    LiquidacionImpactoVialPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_impacto_vial_legacy_schemas import (
    LiquidacionImpactoVialLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_impacto_vial_schemas import (
    LiquidacionImpactoVialOutput,
)


@api_controller("/liquidaciones/impacto-vial", tags=["Impacto Vial Legacy"], permissions=[AllowAny])
class LiquidacionImpactoVialLegacyController:
    """
    Legacy controller for Impacto Vial (PorcentajeObra) with historical fecha_registro (supports any numero_revision).
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionImpactoVialLegacyOrchestrator,
        presenter: LiquidacionImpactoVialPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion",
        response={200: ApiResponse[LiquidacionImpactoVialOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionImpactoVialLegacyIn):
        """
        Crea el Impacto Vial con tarifas históricas basadas en fecha_registro.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación legacy de impacto vial creada correctamente.")
