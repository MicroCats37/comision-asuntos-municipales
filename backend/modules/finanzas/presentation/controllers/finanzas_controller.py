"""
FinanzasController — controladores HTTP ligeros para finanzas.

Solo delega a FinanzasOrchestrator.
"""
import uuid
from ninja import Query

from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    VariablesFinancierasOut,
    ReciboHonorarioCrearIn,
    ReciboHonorarioDelegadoOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas"], permissions=[AllowAny])
class FinanzasController:
    """
    Controlador para Finanzas.

    Endpoints:
    - GET /variables/vigentes: Obtiene IGV y UIT vigentes para mostrar en formulario
    - POST /recibos-honorarios: Crea ReciboHonorarioDelegado para una LiquidacionDelegado
    - GET /recibos-honorarios: Lista recibos con paginación y filtros por delegado/liquidacion
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

    @route.post(
        "/recibos-honorarios",
        response={200: ApiResponse[ReciboHonorarioDelegadoOut]},
        auth=None,
    )
    def crear_recibo_honorario(self, request, payload: ReciboHonorarioCrearIn):
        """
        Crea o actualiza un ReciboHonorarioDelegado para una LiquidacionDelegado.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_result = self.orchestrator.crear_recibo_proceso(
            liquidacion_delegado_id=payload.liquidacion_delegado_id,
        )
        presented = FinanzasPresenter.present_recibo(domain_result)
        return success_response(presented)

    @route.get(
        "/recibos-honorarios",
        response={200: ApiResponse[PaginatedData[ReciboHonorarioDelegadoOut]]},
        auth=None,
    )
    def listar_recibos(
        self,
        request,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        delegado_id: uuid.UUID | None = None,
        liquidacion_id: uuid.UUID | None = None,
    ):
        """
        Lista recibos de honorarios con paginación.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_results, total = self.orchestrator.listar_recibos_proceso(
            page=page,
            page_size=page_size,
            delegado_id=delegado_id,
            liquidacion_id=liquidacion_id,
        )
        presented = FinanzasPresenter.present_recibos_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)
