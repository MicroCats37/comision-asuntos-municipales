"""
LiquidacionDelegadoController — Thin HTTP controller for delegados de liquidación.

Endpoints:
- GET   /api/liquidaciones/delegados/vigentes
- GET   /api/liquidaciones/delegados-asignaciones
- PATCH /api/liquidaciones/{liquidacion_id}/delegados

NO business logic. Only: parse input, call orchestrator, map via presenter.
"""
import uuid
from datetime import date
from typing import Optional

from injector import inject
from ninja import Query
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.orchestrators.delegados_batch_orchestrator import (
    DelegadosBatchOrchestrator,
)
from modules.liquidaciones.presentation.presenters.delegado_presenter import (
    DelegadoPresenter,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    DelegadosVigentesOut,
    LiquidacionDelegadoBatchIn,
    LiquidacionDelegadoBatchOut,
    LiquidacionDelegadoOut,
)


@api_controller("/liquidaciones", tags=["Delegados de Liquidación"], permissions=[AllowAny])
class LiquidacionDelegadoController:
    """
    Controller for delegados vigentes and LiquidacionDelegado batch endpoints.
    """

    @inject
    def __init__(
        self,
        delegados_batch_orchestrator: DelegadosBatchOrchestrator,
        presenter: DelegadoPresenter,
    ):
        self.orchestrator = delegados_batch_orchestrator
        self.presenter = presenter

    @route.get(
        "/delegados/vigentes",
        response={200: ApiResponse[DelegadosVigentesOut]},
        auth=None,
    )
    def list_delegados_vigentes(
        self,
        municipalidad_id: uuid.UUID,
        tipo_liquidacion: str,
        revision_id: Optional[uuid.UUID] = None,
        fecha: Optional[date] = None,
    ):
        """
        GET /liquidaciones/delegados/vigentes?municipalidad_id=&tipo_liquidacion=&revision_id=&fecha=YYYY-MM-DD

        Delegados cuyo especialidad_revision pertenece a las especialidades vigentes
        del tipo de liquidación y con asignación municipal vigente.

        When `fecha` is provided, resolves vigentes at that date.
        When omitted, defaults to today for backward compatibility.
        """
        domain_result = self.orchestrator.obtener_delegados_vigentes_proceso(
            municipalidad_id=municipalidad_id,
            tipo_liquidacion=tipo_liquidacion,
            revision_id=revision_id,
            fecha=fecha,
        )
        return success_response(
            self.presenter.present_delegados_vigentes(domain_result)
        )

    @route.get(
        "/delegados-asignaciones",
        response={200: ApiResponse[PaginatedData[LiquidacionDelegadoOut]]},
        auth=None,
    )
    def list_delegados_asignaciones(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        cip: Optional[str] = Query(None),
        liquidacion_id: Optional[uuid.UUID] = Query(None),
    ):
        """
        GET /liquidaciones/delegados-asignaciones?page=&page_size=&cip=&liquidacion_id=

        Lista paginada de asignaciones LiquidacionDelegado para el selector
        de Recibos de Honorarios. Cada item incluye liquidacion{}, delegado{}
        y especialidad_revision{} anidados.
        """
        results, total = self.orchestrator.listar_asignaciones_proceso(
            page=page,
            page_size=page_size,
            cip=cip,
            liquidacion_id=liquidacion_id,
        )
        return success_response(
            self.presenter.present_asignaciones_list(results, total, page, page_size)
        )

    @route.patch(
        "/{liquidacion_id}/delegados",
        response={200: ApiResponse[LiquidacionDelegadoBatchOut]},
        auth=None,
    )
    def batch_delegados(
        self,
        liquidacion_id: uuid.UUID,
        payload: LiquidacionDelegadoBatchIn,
    ):
        """
        PATCH /liquidaciones/{liquidacion_id}/delegados

        Batch create/update/delete de LiquidacionDelegado en una única transacción.
        """
        batch_result = self.orchestrator.procesar_batch_delegados_proceso(
            liquidacion_id=liquidacion_id,
            payload=payload,
        )
        return success_response(
            self.presenter.present_liquidacion_delegado_batch(batch_result)
        )
