"""
HTTP Controller for Edificaciones (PorcentajeObra) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/edificaciones/legacy/nueva-liquidacion/primera-revision

Thin controller — only delegates, no logic.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_edificaciones_legacy_orchestrator import (
    LiquidacionEdificacionesLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_edificaciones_presenter import (
    LiquidacionEdificacionesPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_edificaciones_legacy_schemas import (
    LiquidacionEdificacionesLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesOutput,
)


@api_controller("/liquidaciones/edificaciones", tags=["Edificaciones Legacy"], permissions=[AllowAny])
class LiquidacionEdificacionesLegacyController:
    """
    Legacy controller for Edificaciones (PorcentajeObra) primera-revision with historical fecha_registro.
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionEdificacionesLegacyOrchestrator,
        presenter: LiquidacionEdificacionesPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionEdificacionesOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionEdificacionesLegacyIn):
        """
        Crea la Edificación con tarifas históricas basadas en fecha_registro.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)
