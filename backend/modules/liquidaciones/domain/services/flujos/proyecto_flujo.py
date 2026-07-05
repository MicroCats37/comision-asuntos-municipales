"""
ProyectoFlujo — flujos async de negocio para proyectos.
"""
from asgiref.sync import sync_to_async
from injector import inject

from ..core.proyecto_core_service import ProyectoService
from ...schemas_proyecto import (
    ProyectoCreateData,
    ProyectoPaginatedResult,
    ProyectoResult,
)


class ProyectoFlujo:
    """
    Flujos async para Proyectos.
    """

    @inject
    def __init__(self, core: ProyectoService):
        self.core = core

    async def _proceso_crear(
        self,
        denominacion: str,
        direccion: str | None,
        distrito_id: str | None,
        entidad_id: str | None,
    ) -> ProyectoResult:
        """
        Proceso para crear un nuevo proyecto.

        Args:
            denominacion: Denominación del proyecto
            direccion: Dirección del proyecto
            distrito_id: ID del distrito
            entidad_id: ID de la entidad

        Returns:
            ProyectoResult con los datos del proyecto creado
        """
        data = ProyectoCreateData(
            denominacion=denominacion,
            direccion=direccion,
            distrito_id=distrito_id,
            entidad_id=entidad_id,
        )

        proyecto = await sync_to_async(self.core._crear_proyecto)(data)
        result = await sync_to_async(self.core._to_result)(proyecto)
        return result

    async def _proceso_buscar_por_public_id(self, public_id: str) -> ProyectoResult | None:
        """
        Proceso para buscar un proyecto por su public_id.

        Args:
            public_id: ID público del proyecto

        Returns:
            ProyectoResult si existe, None si no
        """
        proyecto = await sync_to_async(self.core._buscar_por_public_id)(public_id)
        if not proyecto:
            return None
        result = await sync_to_async(self.core._to_result)(proyecto)
        return result

    async def _proceso_listar_con_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
    ) -> ProyectoPaginatedResult:
        """
        Lista todos los proyectos con sus liquidaciones de edificaciones,
        con paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página

        Returns:
            ProyectoPaginatedResult con items y total
        """
        return await sync_to_async(self.core._listar_proyectos_con_liquidaciones_paginado)(
            page=page,
            page_size=page_size,
        )
