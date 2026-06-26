"""
ProyectistaOrchestrator — fachada asíncrona ligera para controladores de proyectistas.

NOTE: Simplificado para usar identificación por (perfil_ingeniero, especialidad).
"""
import uuid
from injector import inject

from ..flujos.proyectista_flujo import ProyectistaFlujo


class ProyectistaOrchestrator:
    """
    Fachada asíncrona ligera para proyectistas.
    """

    @inject
    def __init__(self, flujo: ProyectistaFlujo):
        self.flujo = flujo

    async def upsert_proyectista(
        self,
        perfil_ingeniero_id: uuid.UUID,
        especialidad_id: uuid.UUID,
        descripcion: str | None = None,
    ) -> tuple[dict, bool]:
        """
        Crea o busca un proyectista por (perfil_ingeniero, especialidad).

        Returns:
            tuple: (dict con datos de proyectista, creado) donde creado=True si se creó, False si se encontró existente
        """
        result, creado = await self.flujo.proceso_upsert(
            perfil_ingeniero_id=str(perfil_ingeniero_id),
            especialidad_id=str(especialidad_id),
            descripcion=descripcion,
        )
        return result.model_dump(mode='json'), creado
