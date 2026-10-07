"""
RH Delegado Detalle Controller — flat paginated list of DetalleHonorarioDelegado rows.

GET /finanzas/recibos-delegados/detalle

Informational only — no POST/PUT/PATCH/DELETE.
"""
import uuid

from injector import inject
from ninja import Query
from ninja.errors import HttpError
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny

from core.pagination import PaginatedData
from core.responses import ApiResponse, success_response
from modules.finanzas.domain.services.finanzas_orchestrator import (
    FinanzasOrchestrator,
)
from modules.finanzas.presentation.presenters.finanzas_presenter import (
    FinanzasPresenter,
)
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    DetalleDelegadoRowOut,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


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
        periodo: int | None = Query(None, ge=2000, le=2100, description="Año del periodo (e.g. 2026). Opcional."),
        mes: int | None = Query(None, ge=1, le=12, description="Mes (1-12). Opcional."),
        municipalidad_id: uuid.UUID | None = Query(None, description="UUID de la municipalidad (liquidacion source, not operation). Opcional."),
        tipo_liquidacion_codigo: str | None = Query(
            None,
            description=f"Código del tipo de liquidación. REQUERIDO. Valores válidos: {', '.join(TipoLiquidacion.values)}",
        ),
        numero_liquidacion: int | None = Query(
            None,
            description="Número de liquidación específico (requiere tipo_liquidacion_codigo). Opcional.",
        ),
    ):
        """
        GET /finanzas/recibos-delegados/detalle — lista filas de DetalleHonorarioDelegado.

        Filtro requerido: tipo_liquidacion_codigo.
        Filtros opcionales: delegado_id, delegado_cip, periodo, mes, municipalidad_id, numero_liquidacion.
        delegado_cip tiene precedencia sobre delegado_id si ambos están presentes.
        municipalidad_id y tipo_liquidacion_codigo se filtran desde la Liquidacion (no desde la operación).
        numero_liquidacion se interpreta según el tipo_liquidacion_codigo para buscar en la tabla específica.

        Returns paginated list of detail rows.
        """
        if tipo_liquidacion_codigo is None:
            raise HttpError(
                400,
                "tipo_liquidacion_codigo es obligatorio para consultar detalle RH.",
            )
        if tipo_liquidacion_codigo not in TipoLiquidacion.values:
            raise HttpError(
                400,
                f"tipo_liquidacion_codigo inválido. Valores válidos: {', '.join(TipoLiquidacion.values)}",
            )

        domain_results, total = self.orchestrator.list_rh_detalle_delegados_proceso(
            page=page,
            page_size=page_size,
            delegado_id=delegado_id,
            delegado_cip=delegado_cip,
            periodo=periodo,
            mes=mes,
            municipalidad_id=municipalidad_id,
            tipo_liquidacion_codigo=tipo_liquidacion_codigo,
            numero_liquidacion=numero_liquidacion,
        )
        presented = FinanzasPresenter.present_rh_detalle_delegados_list(
            domain_results, total, page, page_size
        )
        return success_response(presented)
