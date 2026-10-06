"""
RH Delegado Detalle Controller — flat paginated list of DetalleHonorarioDelegado rows.

GET /finanzas/recibos-delegados/detalle

Informational only — no POST/PUT/PATCH/DELETE.
"""
import uuid
from ninja import Query
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja.errors import HttpError

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    DetalleDelegadoRowOut,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter


@api_controller("/finanzas", tags=["Finanzas-RH-Delegado-Detalle"], permissions=[AllowAny])
class RHDelegadoDetalleController:
    """
    Controlador para listar filas sueltas de DetalleHonorarioDelegado (detalle flat).

    Endpoints:
    - GET /finanzas/recibos-delegados/detalle — lista paginada de filas detalle
    """

    @inject
    def __init__(self, orchestrator: FinanzasOrchestrator):
        self.orchestrator = orchestrator

    @route.get(
        "/recibos-delegados/detalle",
        response={200: ApiResponse[PaginatedData[DetalleDelegadoRowOut]]},
        auth=None,
    )
    def listar_rh_delegado_detalle(
        self,
        request,
        page: int = Query(1, ge=1, description="Página (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Elementos por página (max 100)"),
        delegado_id: uuid.UUID | None = Query(None, description="UUID del delegado"),
        delegado_cip: str | None = Query(None, description="CIP del delegado"),
        periodo: int | None = Query(None, ge=2000, le=2100, description="Año del periodo (e.g. 2026)"),
        mes: int | None = Query(None, ge=1, le=12, description="Mes (1-12)"),
        municipalidad_id: uuid.UUID | None = Query(None, description="UUID de la municipalidad (liquidacion source, not operation)"),
        tipo_liquidacion_id: uuid.UUID | None = Query(None, description="UUID del tipo de liquidación (from Liquidacion)"),
        numero_liquidacion: int | None = Query(None, description="Número de liquidación específico (requiere tipo_liquidacion_id)"),
    ):
        """
        GET /finanzas/recibos-delegados/detalle — lista filas de DetalleHonorarioDelegado.

        Filtros requeridos: periodo, tipo_liquidacion_id.
        Filtros opcionales: delegado_id, delegado_cip, mes, municipalidad_id, numero_liquidacion.
        delegadow_cip tiene precedencia sobre delegado_id si ambos están presentes.
        municipalidad_id y tipo_liquidacion_id se filtran desde la Liquidacion (no desde la operación).
        numero_liquidacion se interpreta según el tipo_liquidacion_id para buscar en la tabla específica.

        Returns paginated list of detail rows.
        """
        # Validate required filters
        if periodo is None or tipo_liquidacion_id is None:
            raise HttpError(
                400,
                "Periodo y tipo de liquidación son obligatorios para consultar detalle RH.",
            )

        domain_results, total = self.orchestrator.list_rh_detalle_delegados_proceso(
            page=page,
            page_size=page_size,
            delegado_id=delegado_id,
            delegado_cip=delegado_cip,
            periodo=periodo,
            mes=mes,
            municipalidad_id=municipalidad_id,
            tipo_liquidacion_id=tipo_liquidacion_id,
            numero_liquidacion=numero_liquidacion,
        )
        presented = FinanzasPresenter.present_rh_detalle_delegados_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)
