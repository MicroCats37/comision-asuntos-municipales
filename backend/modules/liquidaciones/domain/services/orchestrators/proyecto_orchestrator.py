"""
ProyectoOrchestrator — fachada asíncrona ligera para controladores de proyectos.
"""
from injector import inject

from ..flujos.proyecto_flujo import ProyectoFlujo


class ProyectoOrchestrator:
    """
    Fachada asíncrona ligera para proyectos.
    """

    @inject
    def __init__(self, flujo: ProyectoFlujo):
        self.flujo = flujo

    async def crear_proyecto(
        self,
        denominacion: str,
        direccion: str | None,
        distrito_id: str | None,
        entidad_id: str | None,
    ) -> dict:
        """
        Crea un nuevo proyecto.

        Returns:
            dict con datos del proyecto creado
        """
        result = await self.flujo._proceso_crear(
            denominacion=denominacion,
            direccion=direccion,
            distrito_id=distrito_id,
            entidad_id=entidad_id,
        )
        return result.model_dump(mode='json')

    async def buscar_por_public_id(self, public_id: str) -> dict | None:
        """
        Busca un proyecto por su public_id.

        Returns:
            dict con datos del proyecto si existe, None si no
        """
        result = await self.flujo._proceso_buscar_por_public_id(public_id)
        if not result:
            return None
        return result.model_dump(mode='json')

    async def listar_proyectos_con_liquidaciones(
        self,
        page: int,
        page_size: int,
    ) -> dict:
        """
        Lista todos los proyectos con sus liquidaciones de edificaciones,
        con paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página

        Returns:
            dict con items y total (para usar con PaginatedData wrapper)
        """
        result = await self.flujo._proceso_listar_con_liquidaciones_paginado(
            page=page,
            page_size=page_size,
        )
        return result.model_dump(mode='json')
