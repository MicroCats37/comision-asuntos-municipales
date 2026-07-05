"""
ProyectoController — controladores HTTP ligeros para proyectos.

Solo delega a ProyectoOrchestrator.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from ..schemas.proyecto_schemas import (
    ProyectoIn,
    ProyectoListItemOut,
    ProyectoUpsertResponseOut,
)
from ...domain.services.orchestrators.proyecto_orchestrator import ProyectoOrchestrator


@api_controller("/proyectos", tags=["Proyectos"], permissions=[AllowAny])
class ProyectoController:
    """
    Controlador para Proyectos.

    Endpoints:
    - GET /: Listar todos los proyectos con liquidaciones (paginado)
    - POST /: Crear proyecto
    - GET /buscar/{public_id}: Buscar proyecto por public_id
    """

    @inject
    def __init__(self, orchestrator: ProyectoOrchestrator):
        self.orchestrator = orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[ProyectoListItemOut]]}, auth=None)
    async def listar_proyectos(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Lista todos los proyectos con sus liquidaciones de edificaciones,
        con paginación.

        Cada proyecto incluye:
        - id, public_id, denominacion, direccion, distrito
        - entidad con id, tipo_documento, numero_documento, nombre
        - liquidaciones.edificaciones: lista de liquidaciones (sin total_edificaciones)
        """
        result = await self.orchestrator.listar_proyectos_con_liquidaciones(
            page=page,
            page_size=page_size,
        )

        total_pages = (result['total'] + page_size - 1) // page_size if result['total'] > 0 else 1

        return success_response(PaginatedData(
            items=result['items'],
            total=result['total'],
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

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
