"""
RH Inspector Mensual Controller — thin HTTP controller.

Endpoints for RH Inspector Mensual (cotizar/crear/candidatos and list).
All delegation to FinanzasOrchestrator.
"""
import uuid
from ninja import Query
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.finanzas.domain.schemas import RHInspectorCotizarIn
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    RHInspectorCotizarOut,
    InspectorCandidatosOut,
    InspectorCandidatosPaginatedOut,
    RHInspectorMensualListItemOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas-RH-Inspector"], permissions=[AllowAny])
class RHInspectorMensualController:
    """
    Controlador para RH Inspector Mensual.

    Endpoints:
    - POST /finanzas/recibos-inspectores/cotizar
    - POST /finanzas/recibos-inspectores/crear
    - GET  /finanzas/recibos-inspectores/candidatos
    - GET  /finanzas/recibos-inspectores
    """

    @inject
    def __init__(self, orchestrator: FinanzasOrchestrator):
        self.orchestrator = orchestrator

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
        return success_response(FinanzasPresenter.present_rh_inspector_mensual(result), message="Recibo de inspector creado correctamente.")

    @route.get(
        "/recibos-inspectores/candidatos",
        response={200: ApiResponse[InspectorCandidatosPaginatedOut]},
        auth=None,
    )
    def listar_candidatas_inspector(
        self,
        cip: str,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        expediente: str | None = Query(default=None),
        numero: int | None = Query(default=None),
        propietario: str | None = Query(default=None),
        direccion: str | None = Query(default=None),
        periodo: str | None = Query(default=None),
        fecha_inicio: str | None = Query(default=None, description="Filter by fecha_registro >= date (YYYY-MM-DD)"),
        fecha_fin: str | None = Query(default=None, description="Filter by fecha_registro <= date (YYYY-MM-DD)"),
    ):
        """
        GET /finanzas/recibos-inspectores/candidatos?cip=...&page=1&page_size=10&expediente=...&numero=...&propietario=...&direccion=...&periodo=...&fecha_inicio=...&fecha_fin=...

        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector
        con paginación y filtros adicionales.

        Las candidatas son las LiquidacionInspector asignadas al inspector que tienen
        saldo_disponible > 0 para el periodo dado.

        Si periodo se proporciona, calcula inspecciones pagadas acumuladas de todos los
        periodos estrictamente anteriores. Si no se proporciona, suma todos los periodos
        históricamente (saldo total disponible).

        Filtros de fecha (opcionales):
        - fecha_inicio: fecha de registro >= fecha_inicio (inclusive)
        - fecha_fin: fecha de registro <= fecha_fin (inclusive)
        - Si fecha_inicio > fecha_fin: retorna 422 con error.

        Filtros de búsqueda (opcionales):
        - expediente: icontains sobre LiquidacionGeneral.expediente
        - numero: exact match sobre el número de la liquidacion IO (LiquidacionPorCategoriaVisitas.numero)
        - propietario: icontains sobre proyecto.nombre_propietario
        - direccion: icontains sobre proyecto.direccion

        Contrato 1A: Controlador sagrado — solo parsea entrada, llama orchestrator,
        retorna success_response formateado por presenter.
        """
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            from ninja.errors import HttpError
            raise HttpError(422, "fecha_inicio no puede ser mayor que fecha_fin")
        result = self.orchestrator.list_candidatos_inspector_proceso_paginated(
            cip,
            page=page,
            page_size=page_size,
            expediente=expediente,
            numero=numero,
            propietario=propietario,
            direccion=direccion,
            periodo=periodo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        return success_response(FinanzasPresenter.present_inspector_candidatos_paginated(result))

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
        GET /finanzas/recibos-inspectores — lista RecibosHonorariosInspectorMensual con paginación.

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
