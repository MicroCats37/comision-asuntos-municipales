"""
ProyectistaController — controladores HTTP ligeros para proyectistas.

Solo delega a ProyectistaOrchestrator.

NOTE: Simplificado para usar identificación por (perfil_ingeniero, especialidad).
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from ..schemas.proyectista_schemas import (
    ProyectistaIn,
    ProyectistaUpsertResponseOut,
)
from ...domain.services.orchestrators.proyectista_orchestrator import ProyectistaOrchestrator


@api_controller("/proyectistas", tags=["Proyectistas"], permissions=[AllowAny])
class ProyectistaController:
    """
    Controlador para Proyectistas.

    Endpoints:
    - POST /: Crear o buscar proyectista por (perfil_ingeniero, especialidad)
    """

    @inject
    def __init__(self, orchestrator: ProyectistaOrchestrator):
        self.orchestrator = orchestrator

    @route.post("/", response={200: ApiResponse[ProyectistaUpsertResponseOut]}, auth=None)
    async def upsert_proyectista(self, payload: ProyectistaIn):
        """
        Crear o buscar un proyectista por (perfil_ingeniero, especialidad).
        """
        result_dict, creado = await self.orchestrator.upsert_proyectista(
            perfil_ingeniero_id=payload.perfil_ingeniero_id,
            especialidad_id=payload.especialidad_id,
            descripcion=payload.descripcion,
        )

        response_data = {
            **result_dict,
            "creado": creado,
        }
        return success_response(response_data)
