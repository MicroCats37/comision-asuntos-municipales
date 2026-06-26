"""
ProyectistaFlujo — flujos async de negocio para proyectistas.

NOTE: Flujo simplificado para usar identificación por (perfil_ingeniero, especialidad).
"""
from asgiref.sync import sync_to_async
from injector import inject

from ..core.proyectista_core_service import ProyectistaService
from ...schemas_proyectista import ProyectistaCreateData, ProyectistaResult


class ProyectistaFlujo:
    """
    Flujos async para Proyectistas.
    """

    @inject
    def __init__(self, core: ProyectistaService):
        self.core = core

    async def proceso_upsert(
        self,
        perfil_ingeniero_id: str,
        especialidad_id: str,
        descripcion: str | None = None,
    ) -> tuple[ProyectistaResult, bool]:
        """
        Proceso para crear o buscar un proyectista por (perfil_ingeniero, especialidad).

        Busca por perfil_ingeniero + especialidad.
        Si no encuentra, crea uno nuevo.

        Returns:
            tuple: (ProyectistaResult, creado) donde creado=True si se creó, False si se encontró existente
        """
        data = ProyectistaCreateData(
            perfil_ingeniero_id=perfil_ingeniero_id,
            especialidad_id=especialidad_id,
            descripcion=descripcion,
        )

        # Buscar si existe por perfil_ingeniero + especialidad
        existente = await sync_to_async(self.core._buscar_por_perfil_y_especialidad)(
            perfil_ingeniero_id, especialidad_id
        )

        if existente:
            # Actualizar con datos nuevos
            proyectista = await sync_to_async(self.core._actualizar_proyectista)(existente, data)
            result = await sync_to_async(self.core._to_result)(proyectista)
            return result, False
        else:
            # Crear
            proyectista = await sync_to_async(self.core._crear_proyectista)(data)
            result = await sync_to_async(self.core._to_result)(proyectista)
            return result, True
