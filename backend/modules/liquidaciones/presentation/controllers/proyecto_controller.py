"""
ProyectoController — controladores HTTP ligeros para proyectos.

Solo delega a ProyectoOrchestrator.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from ..schemas.proyecto_schemas import (
    ProyectoIn,
    ProyectoUpsertResponseOut,
)
from ...domain.services.orchestrators.proyecto_orchestrator import ProyectoOrchestrator


@api_controller("/proyectos", tags=["Proyectos"], permissions=[AllowAny])
class ProyectoController:
    """
    Controlador para Proyectos.

    Endpoints:
    - POST /: Crear proyecto
    - GET /buscar/{public_id}: Buscar proyecto por public_id
    """

    @inject
    def __init__(self, orchestrator: ProyectoOrchestrator):
        self.orchestrator = orchestrator

    @route.post("/", response={200: ApiResponse[ProyectoUpsertResponseOut]}, auth=None)
    async def crear_proyecto(self, payload: ProyectoIn):
        """
        Crear un nuevo proyecto.

        El proyecto recibe un public_id auto-generado.
        """
        result = await self.orchestrator.crear_proyecto(
            denominacion=payload.denominacion,
            direccion=payload.direccion,
            distrito_id=payload.distrito_id,
            entidad_id=payload.entidad_id,
        )
        return success_response(result)

    @route.get("/buscar/{public_id}", response={200: ApiResponse[ProyectoUpsertResponseOut]}, auth=None)
    async def buscar_proyecto(self, public_id: str):
        """
        Buscar un proyecto por su public_id.

        Returns None si no existe.
        """
        result = await self.orchestrator.buscar_por_public_id(public_id)
        if not result:
            return success_response(None)
        return success_response(result)
