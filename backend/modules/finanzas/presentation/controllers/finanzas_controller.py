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
from modules.finanzas.domain.schemas import RHInspectorCotizarIn
from modules.finanzas.domain.schemas import RHDelegadoCotizarIn
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    VariablesFinancierasOut,
    ReciboHonorarioDelegadoCrearIn,
    ReciboHonorarioDelegadoOut,
    ReciboHonorarioInspectorCrearIn,
    ReciboHonorarioInspectorOut,
    RHInspectorCotizarOut,
    InspectorCandidatosOut,
    RHDelegadoCotizarOut,
    RHDelegadoMensualListItemOut,
    RHInspectorMensualListItemOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas"], permissions=[AllowAny])
class FinanzasController:
    """
    Controlador para Finanzas.

    Endpoints:
    - GET /variables/vigentes: Obtiene IGV y UIT vigentes para mostrar en formulario
    - POST /recibos-delegados: Crea ReciboHonorarioDelegado para una LiquidacionDelegado
    - GET /recibos-delegados: Lista recibos con paginación y filtros por delegado/liquidacion
    - POST /recibos-inspectores: Crea ReciboHonorarioInspector para una LiquidacionInspector
    - GET /recibos-inspectores: Lista recibos de inspectores con paginación y filtros
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
        "/recibos-delegados",
        response={200: ApiResponse[ReciboHonorarioDelegadoOut]},
        auth=None,
    )
    def crear_recibo_honorario(self, request, payload: ReciboHonorarioDelegadoCrearIn):
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
        "/recibos-delegados",
        response={200: ApiResponse[PaginatedData[RHDelegadoMensualListItemOut]]},
        auth=None,
    )
    def listar_recibos(
        self,
        request,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        delegado_id: uuid.UUID | None = None,
    ):
        """
        Lista RecibosHonorariosDelegadoMensuales con paginación.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_results, total = self.orchestrator.listar_rh_mensual_delegados_proceso(
            page=page,
            page_size=page_size,
            delegado_id=delegado_id,
        )
        presented = FinanzasPresenter.present_rh_mensuales_delegado_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)

    @route.post(
        "/recibos-inspectores",
        response={200: ApiResponse[ReciboHonorarioInspectorOut]},
        auth=None,
    )
    def crear_recibo_inspector(
        self, request, payload: ReciboHonorarioInspectorCrearIn
    ):
        """
        Crea un ReciboHonorarioInspector para una LiquidacionInspector.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_result = self.orchestrator.crear_recibo_inspector_proceso(
            liquidacion_inspector_id=payload.liquidacion_inspector_id,
            inspecciones_mes=payload.inspecciones_mes,
        )
        presented = FinanzasPresenter.present_recibo_inspector(domain_result)
        return success_response(presented)

    @route.get(
        "/recibos-inspectores",
        response={200: ApiResponse[PaginatedData[RHInspectorMensualListItemOut]]},
        auth=None,
    )
    def listar_recibos_inspectores(
        self,
        request,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        inspector_id: uuid.UUID | None = None,
    ):
        """
        Lista RecibosHonorariosInspectorMensuales con paginación.

        Agrupa por periodo (YYYY-MM) + inspector, mostrando totales y detalles.
        Reemplaza el antiguo listado de recibos individuales por LiquidacionInspector.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        domain_results, total = self.orchestrator.listar_rh_mensual_inspectores_proceso(
            page=page,
            page_size=page_size,
            inspector_id=inspector_id,
        )
        presented = FinanzasPresenter.present_rh_mensuales_inspector_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)

    # ── RH Inspector Mensual ─────────────────────────────────────────────────────

    @route.post(
        "/recibos-inspectores/cotizar",
        response={200: ApiResponse[RHInspectorCotizarOut]},
        auth=None,
    )
    def cotizar_rh_inspector_mensual(self, request, payload: RHInspectorCotizarIn):
        """
        POST /finanzas/recibos-inspectores/cotizar — calcula sin crear.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.cotizar_rh_inspector_mensual_proceso(payload)
        return success_response(FinanzasPresenter.present_rh_inspector_mensual(result))

    @route.post(
        "/recibos-inspectores/crear",
        response={200: ApiResponse[RHInspectorCotizarOut]},
        auth=None,
    )
    def crear_rh_inspector_mensual(self, request, payload: RHInspectorCotizarIn):
        """
        POST /finanzas/recibos-inspectores/crear — crea la maestra + detalles.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.crear_rh_inspector_mensual_proceso(payload)
        return success_response(FinanzasPresenter.present_rh_inspector_mensual(result))

    @route.get(
        "/recibos-inspectores/candidatos",
        response={200: ApiResponse[InspectorCandidatosOut]},
        auth=None,
    )
    def listar_candidatas_inspector(
        self,
        cip: str,
        periodo: str | None = Query(default=None),
        fecha_inicio: str | None = Query(default=None, description="Filter by fecha_registro >= date (YYYY-MM-DD)"),
        fecha_fin: str | None = Query(default=None, description="Filter by fecha_registro <= date (YYYY-MM-DD)"),
    ):
        """
        GET /finanzas/recibos-inspectores/candidatos?cip=...&periodo=...&fecha_inicio=...&fecha_fin=...

        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector.
        Las candidatas son las LiquidacionInspector asignadas al inspector que tienen
        saldo_disponible > 0 para el periodo dado.

        Si periodo se proporciona, calcula inspecciones pagadas acumuladas de todos los
        periodos estrictamente anteriores. Si no se proporciona, suma todos los periodos
        históricamente (saldo total disponible).

        Filtros de fecha (opcionales):
        - fecha_inicio: fecha de registro >= fecha_inicio (inclusive)
        - fecha_fin: fecha de registro <= fecha_fin (inclusive)
        - Si fecha_inicio > fecha_fin: retorna 422 con error.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            from ninja.errors import HttpError
            raise HttpError(422, "fecha_inicio no puede ser mayor que fecha_fin")
        result = self.orchestrator.list_candidatos_inspector_proceso(
            cip, periodo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
        )
        return success_response(FinanzasPresenter.present_inspector_candidatos(result))

    # ── RH Delegado Mensual ─────────────────────────────────────────────────────

    @route.post(
        "/recibos-delegados/cotizar",
        response={200: ApiResponse[RHDelegadoCotizarOut]},
        auth=None,
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
        auth=None,
    )
    def crear_rh_delegado_mensual(self, request, payload: RHDelegadoCotizarIn):
        """
        POST /finanzas/recibos-delegados/crear — crea la maestra + detalles.

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        result = self.orchestrator.crear_rh_delegado_mensual_proceso(payload)
        return success_response(FinanzasPresenter.present_rh_delegado_mensual(result))
