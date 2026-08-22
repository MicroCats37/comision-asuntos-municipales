"""
HTTP Controller for Inspección de Obra (Visitas) legacy endpoint.

100% additive — no existing controller modified.

Endpoints:
- POST /api/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion

Thin controller — only delegates, no logic.

NOTE: Inspección de Obra always inherits proyecto/municipalidad/entidad from a previous
liquidacion (Edificación or HU), so the legacy schema includes liquidacion_previa_id.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_inspeccion_obra_legacy_orchestrator import (
    LiquidacionInspeccionObraLegacyOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_inspeccion_obra_presenter import (
    LiquidacionInspeccionObraPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_inspeccion_obra_legacy_schemas import (
    LiquidacionInspeccionObraLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOutput,
)


@api_controller("/liquidaciones/inspeccion-obra", tags=["Inspección de Obra Legacy"], permissions=[AllowAny])
class LiquidacionInspeccionObraLegacyController:
    """
    Legacy controller for Inspección de Obra (Visitas) primera-revision with historical fecha_registro.
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionInspeccionObraLegacyOrchestrator,
        presenter: LiquidacionInspeccionObraPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post(
        "/legacy/nueva-liquidacion",
        response={200: ApiResponse[LiquidacionInspeccionObraOutput]},
    )
    def crear_legacy(self, request, payload: LiquidacionInspeccionObraLegacyIn):
        """
        Crea la Inspección de Obra con tarifas históricas basadas en fecha_registro.
        Hereda proyecto/municipalidad/entidad de la liquidacion_previa_id.
        """
        usuario_id = request.auth.id

        domain_result = self.orchestrator.crear_legacy_proceso(
            usuario_id=usuario_id,
            payload=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)
