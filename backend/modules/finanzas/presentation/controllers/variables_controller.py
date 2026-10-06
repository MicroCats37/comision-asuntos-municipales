"""
Variables Controller — thin HTTP controller.

Endpoint for shared financial variables.
All delegation to FinanzasOrchestrator.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    VariablesFinancierasOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas"], permissions=[AllowAny])
class VariablesController:
    """
    Controlador para Variables Financieras compartidas.

    Endpoints:
    - GET /finanzas/variables/vigentes
    """

    @inject
    def __init__(self, orchestrator: FinanzasOrchestrator):
        self.orchestrator = orchestrator

    @route.get("/variables/vigentes", response={200: ApiResponse[VariablesFinancierasOut]}, auth=None)
    def obtener_variables_vigentes(self):
        """
        Obtiene las variables financieras vigentes (IGV y UIT) para mostrar en formulario.

        Nota: Estos valores son SOLO para mostrar. El cálculo real de liquidaciones
        obtiene internamente los valores vigentes desde el servicio.
        """
        domain_result = self.orchestrator.obtener_variables_vigentes()
        presented = FinanzasPresenter.present_variables_vigentes(domain_result)
        return success_response(presented)
