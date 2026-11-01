"""
RH Delegado Mensual Controller — thin HTTP controller.

Endpoints for RH Delegado Mensual (cotizar/crear and list).
All delegation to FinanzasOrchestrator.
"""
import uuid
from ninja import Query, Path
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.finanzas.domain.schemas import (
    RHDelegadoActualizarIn,
    RHDelegadoCotizarIn,
)
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    RHDelegadoCotizarOut,
    RHDelegadoMensualListItemOut,
    RHDelegadoDeleteOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas-RH-Delegado"], permissions=[AllowAny])
class RHDelegadoMensualController:
    """
    Controlador para RH Delegado Mensual.

    Endpoints:
    - POST /finanzas/recibos-delegados/cotizar
    - POST /finanzas/recibos-delegados/crear
    - GET  /finanzas/recibos-delegados
    - PATCH /finanzas/recibos-delegados/{rh_id}
    """

    @inject
    def __init__(self, orchestrator: FinanzasOrchestrator):
        self.orchestrator = orchestrator

    @route.post(
        "/recibos-delegados/cotizar",
        response={200: ApiResponse[RHDelegadoCotizarOut]},
    )
    def cotizar_rh_delegado_mensual(self, request, payload: RHDelegadoCotizarIn):
        """
        POST /finanzas/recibos-delegados/cotizar — calcula sin crear.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.cotizar_rh_delegado_mensual_proceso(payload)
        return success_response(FinanzasPresenter.present_rh_delegado_mensual(result))

    @route.post(
        "/recibos-delegados/crear",
        response={200: ApiResponse[RHDelegadoCotizarOut]},
    )
    def crear_rh_delegado_mensual(self, request, payload: RHDelegadoCotizarIn):
        """
        POST /finanzas/recibos-delegados/crear — crea la maestra + detalles.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.crear_rh_delegado_mensual_proceso(payload)
        return success_response(FinanzasPresenter.present_rh_delegado_mensual(result), message="Recibo de delegado creado correctamente.")

    @route.get(
        "/recibos-delegados",
        response={200: ApiResponse[PaginatedData[RHDelegadoMensualListItemOut]]},
    )
    def listar_recibos_delegados(
        self,
        request,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        delegado_cip: str | None = Query(None, description="CIP del ingeniero delegado"),
        municipalidad_id: uuid.UUID | None = Query(None, description="UUID de la municipalidad"),
        periodo: int | None = Query(None, ge=2000, le=2100, description="Año del periodo (e.g. 2026)"),
        mes: int | None = Query(None, ge=1, le=12, description="Mes (1-12)"),
        sin_paginacion: bool = Query(
            False,
            description=(
                "Devuelve el conjunto completo filtrado en una sola respuesta "
                "(sin paginación). Útil para exportar la lista completa."
            ),
        ),
    ):
        """
        GET /finanzas/recibos-delegados — lista RecibosHonorariosDelegadoMensual con paginación.

        Filtros: delegado_cip (CIP del ingeniero), municipalidad_id, periodo, mes.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_results, total = self.orchestrator.listar_rh_mensual_delegados_proceso(
            page=page,
            page_size=page_size,
            delegado_cip=delegado_cip,
            municipalidad_id=municipalidad_id,
            periodo=periodo,
            mes=mes,
            sin_paginacion=sin_paginacion,
        )
        presented = FinanzasPresenter.present_rh_mensuales_delegado_list(
            domain_results, total, page, page_size, sin_paginacion
        )
        return success_response(presented)

    @route.delete(
        "/recibos-delegados/{id}/eliminar",
        response={200: ApiResponse[RHDelegadoDeleteOut]},
    )
    def eliminar_recibo_delegado(self, request, id: uuid.UUID = Path(...)):
        """
        DELETE /finanzas/recibos-delegados/{id}/eliminar — elimina un ReciboHonorarioDelegadoMensual.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response.
        """
        self.orchestrator.eliminar_rh_delegado_mensual_proceso(id)
        return success_response(
            RHDelegadoDeleteOut(
                id=id, message="Recibo de delegado eliminado correctamente."
            ),
            message="Recibo de delegado eliminado correctamente.",
        )

    @route.patch(
        "/recibos-delegados/{rh_id}",
        response={200: ApiResponse[RHDelegadoCotizarOut]},
    )
    def actualizar_recibo_delegado(
        self,
        request,
        rh_id: uuid.UUID,
        payload: RHDelegadoActualizarIn,
    ):
        """
        PATCH /finanzas/recibos-delegados/{rh_id} — sincroniza el conjunto final de detalles.

        El conjunto de items del payload es el conjunto FINAL de liquidaciones del
        recibo: los detalles persistidos que no se incluyen se retiran (y su
        asignación se limpia solo si fue creada por el RH y no está compartida).

        No modifica la metadata compartida de la asignación (número de RH, periodo,
        mes, dictamen ni fechas) ni toca Delegado o DelegadoOperacion.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.actualizar_rh_delegado_mensual_proceso(rh_id, payload)
        return success_response(
            FinanzasPresenter.present_rh_delegado_mensual(result),
            message="Recibo de delegado actualizado correctamente.",
        )
