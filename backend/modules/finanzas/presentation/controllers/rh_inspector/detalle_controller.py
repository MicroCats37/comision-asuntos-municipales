"""
RH Inspector Detalle Controller — flat paginated list of DetalleHonorarioInspector rows.

GET /finanzas/recibos-inspectores/detalle

Informational only — no POST/PUT/PATCH/DELETE.
"""
import uuid
from ninja import Query
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    DetalleInspectorRowOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas-RH-Inspector-Detalle"], permissions=[AllowAny])
class RHInspectorDetalleController:
    """
    Controlador para listar filas sueltas de DetalleHonorarioInspector (detalle flat).

    Endpoints:
    - GET /finanzas/recibos-inspectores/detalle — lista paginada de filas detalle
    """

    @inject
    def __init__(self, orchestrator: FinanzasOrchestrator):
        self.orchestrator = orchestrator

    @route.get(
        "/recibos-inspectores/detalle",
        response={200: ApiResponse[PaginatedData[DetalleInspectorRowOut]]},
        auth=None,
    )
    def listar_rh_inspector_detalle(
        self,
        request,
        page: int = Query(1, ge=1, description="Página (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Elementos por página (max 100)"),
        inspector_id: uuid.UUID | None = Query(None, description="UUID del inspector"),
        inspector_cip: str | None = Query(None, description="CIP del inspector"),
        periodo: int | None = Query(None, ge=2000, le=2100, description="Año del periodo (e.g. 2026)"),
        mes: int | None = Query(None, ge=1, le=12, description="Mes (1-12)"),
        municipalidad_id: uuid.UUID | None = Query(None, description="UUID de la municipalidad (from Liquidacion)"),
        numero_liquidacion: int | None = Query(None, description="Número de liquidación específico de Inspección de Obra"),
    ):
        """
        GET /finanzas/recibos-inspectores/detalle — lista filas de DetalleHonorarioInspector.

        Filtros opcionales: inspector_id, inspector_cip, periodo, mes, municipalidad_id, numero_liquidacion.
        inspector_cip tiene precedencia sobre inspector_id si ambos están presentes.
        numero_liquidacion busca en la liquidación específica de Inspección de Obra.

        Returns paginated list of detail rows.
        """
        domain_results, total = self.orchestrator.list_rh_detalle_inspectores_proceso(
            page=page,
            page_size=page_size,
            inspector_id=inspector_id,
            inspector_cip=inspector_cip,
            periodo=periodo,
            mes=mes,
            municipalidad_id=municipalidad_id,
            numero_liquidacion=numero_liquidacion,
        )
        presented = FinanzasPresenter.present_rh_detalle_inspectores_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)
