# -*- coding: utf-8 -*-
"""
RHReparticionEstacional Controller — thin HTTP controller.

Endpoints for RH Reparticion Estacional (cotizar, crear, list, detail, delete).
All delegation to RHReparticionEstacionalOrchestrator.
"""
from ninja import Query
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.finanzas.domain.schemas import (
    RHReparticionEstacionalCotizarIn,
    RHReparticionEstacionalCrearIn,
)
from modules.finanzas.presentation.schemas.rh_reparticion_estacional_schemas import (
    RHReparticionEstacionalCotizarOut,
    RHReparticionEstacionalListItemOut,
    RHReparticionEstacionalDetalleOut,
    RHReparticionEstacionalDeleteOut,
)
from modules.finanzas.domain.services.orchestrators.rh_reparticion_estacional_orchestrator import (
    RHReparticionEstacionalOrchestrator,
)
from modules.finanzas.presentation.presenters.rh_reparticion_estacional_presenter import (
    RHReparticionEstacionalPresenter,
)


@api_controller("/finanzas", tags=["Finanzas-RH-Reparticion-Estacional"], permissions=[AllowAny])
class RHReparticionEstacionalController:
    """
    Controlador para Repartición Estacional del Fondo Común.

    Endpoints:
    - POST /finanzas/reparticiones-estacionales/cotizar
    - POST /finanzas/reparticiones-estacionales
    - GET  /finanzas/reparticiones-estacionales
    - GET  /finanzas/reparticiones-estacionales/{id}
    - DELETE /finanzas/reparticiones-estacionales/{id}
    """

    @inject
    def __init__(self, orchestrator: RHReparticionEstacionalOrchestrator):
        self.orchestrator = orchestrator

    @route.post(
        "/reparticiones-estacionales/cotizar",
        response={200: ApiResponse[RHReparticionEstacionalCotizarOut]},
        auth=None,
    )
    def cotizar(self, request, payload: RHReparticionEstacionalCotizarIn):
        """
        POST /finanzas/reparticiones-estacionales/cotizar — preview sin persistir.

        Calcula la distribución del fondo_comun sin guardar nada.
        """
        result = self.orchestrator.cotizar_proceso(payload)
        return success_response(RHReparticionEstacionalPresenter.present_cotizar(result))

    @route.post(
        "/reparticiones-estacionales",
        response={200: ApiResponse[RHReparticionEstacionalCotizarOut]},
        auth=None,
    )
    def crear(self, request, payload: RHReparticionEstacionalCrearIn):
        """
        POST /finanzas/reparticiones-estacionales — crea la distribución persistida.

        Valida, calcula y persiste atómicamente.
        """
        result = self.orchestrator.crear_proceso(payload)
        return success_response(RHReparticionEstacionalPresenter.present_cotizar(result), message="Repartición estacional creada correctamente.")

    @route.get(
        "/reparticiones-estacionales",
        response={200: ApiResponse[list[RHReparticionEstacionalListItemOut]]},
        auth=None,
    )
    def listar(
        self,
        request,
        especialidad_revision_id: str | None = Query(None, description="UUID de EspecialidadRevision"),
        periodo: int | None = Query(None, description="Año de la repartición"),
    ):
        """
        GET /finanzas/reparticiones-estacionales — lista reparticiones activas.

        Filtros opcionales por especialidad_revision_id y/o periodo.
        """
        results = self.orchestrator.listar_proceso(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
        )
        presented = [RHReparticionEstacionalPresenter.present_list_item(r) for r in results]
        return success_response(presented)

    @route.get(
        "/reparticiones-estacionales/{reparticion_id}",
        response={200: ApiResponse[RHReparticionEstacionalDetalleOut]},
        auth=None,
    )
    def obtener_detalle(self, request, reparticion_id: str):
        """
        GET /finanzas/reparticiones-estacionales/{id} — detalle completo.

        Incluye los detalles de delegados y capítulos.
        """
        result = self.orchestrator.obtener_detalle_proceso(reparticion_id)
        return success_response(RHReparticionEstacionalPresenter.present_detalle(result))

    @route.delete(
        "/reparticiones-estacionales/{reparticion_id}",
        response={200: ApiResponse[RHReparticionEstacionalDeleteOut]},
        auth=None,
    )
    def eliminar(self, request, reparticion_id: str):
        """
        DELETE /finanzas/reparticiones-estacionales/{id} — soft-delete.

        No elimina físicamente el registro.
        """
        result = self.orchestrator.eliminar_proceso(reparticion_id)
        return success_response(RHReparticionEstacionalDeleteOut(message=result["message"]))
