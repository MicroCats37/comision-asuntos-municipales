"""
FinanzasController — controladores HTTP ligeros para finanzas.

Solo delega a FinanzasOrchestrator.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from ..schemas.finanzas_schemas import VariablesFinancierasOut

# TODO: 重建 FinanzasOrchestrator 后重新启用
# from ...domain.services.finanzas_orchestrator import FinanzasOrchestrator


@api_controller("/finanzas", tags=["Finanzas"], permissions=[AllowAny])
class FinanzasController:
    """
    Controlador para Finanzas.

    Endpoints:
    - GET /variables/vigentes: Obtiene IGV y UIT vigentes para mostrar en formulario
    """

    # TODO: 重建 FinanzasOrchestrator 后重新启用
    # @inject
    # def __init__(self, orchestrator: FinanzasOrchestrator):
    #     self.orchestrator = orchestrator

    @route.get("/variables/vigentes", response={200: ApiResponse[VariablesFinancierasOut]}, auth=None)
    async def obtener_variables_vigentes(self):
        """
        Obtiene las variables financieras vigentes (IGV y UIT) para mostrar en formulario.

        Nota: Estos valores son SOLO para mostrar. El cálculo real de liquidaciones
        obtiene internamente los valores vigentes desde el servicio.
        """
        # TODO: 重建后实现
        return success_response({
            "igv": None,
            "uit": None,
            "message": "FinanzasOrchestrator pendiente de reconstruir"
        })
