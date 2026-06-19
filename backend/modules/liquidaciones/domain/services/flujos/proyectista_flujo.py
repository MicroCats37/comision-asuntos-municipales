"""
ProyectistaFlujo — flujos async de negocio para proyectistas.
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

    async def _proceso_upsert(
        self,
        nombres: str,
        apellidos: str,
        cip: str | None,
        dni: str | None,
        cap: str | None,
    ) -> tuple[ProyectistaResult, bool]:
        """
        Proceso para crear o buscar un proyectista.

        Busca por DNI si existe, si no encuentra busca por CIP.
        Si no encuentra ninguno, crea uno nuevo.

        Returns:
            tuple: (ProyectistaResult, creado) donde creado=True si se creó, False si se encontró existente
        """
        data = ProyectistaCreateData(
            nombres=nombres,
            apellidos=apellidos,
            cip=cip,
            dni=dni,
            cap=cap,
        )

        # Buscar si existe por DNI o CIP
        existente = None
        if dni:
            existente = await sync_to_async(self.core._buscar_por_dni)(dni)
        if not existente and cip:
            existente = await sync_to_async(self.core._buscar_por_cip)(cip)

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
