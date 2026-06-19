"""
EntidadesFlujo — flujos async de negocio para entidades.
"""
from asgiref.sync import sync_to_async
from injector import inject

from ..entidades_core_service import EntidadesCoreService
from ...schemas import EntidadCreateData, EntidadResult


class EntidadFlujo:
    """
    Flujos async para Entidades.
    """

    @inject
    def __init__(self, core: EntidadesCoreService):
        self.core = core

    async def _proceso_upsert(
        self,
        tipo_documento: str,
        numero_documento: str,
        razon_social: str | None,
        nombres: str | None,
        apellidos: str | None,
        nombre_comercial: str | None,
        direccion: str | None,
        distrito_id: str | None,
    ) -> tuple[EntidadResult, bool]:
        """
        Proceso para crear o actualizar una entidad.

        Returns:
            tuple: (EntidadResult, creado) donde creado=True si se creó, False si se actualizó
        """
        data = EntidadCreateData(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            razon_social=razon_social,
            nombres=nombres,
            apellidos=apellidos,
            nombre_comercial=nombre_comercial,
            direccion=direccion,
            distrito_id=distrito_id,
        )

        # Buscar si existe
        existente = await sync_to_async(self.core._buscar_por_numero_documento)(numero_documento)

        if existente:
            # Actualizar
            entidad = await sync_to_async(self.core._actualizar_entidad)(existente, data)
            result = await sync_to_async(self.core._to_result)(entidad)
            return result, False
        else:
            # Crear
            entidad = await sync_to_async(self.core._crear_entidad)(data)
            result = await sync_to_async(self.core._to_result)(entidad)
            return result, True

    async def _proceso_buscar_por_documento(self, numero_documento: str) -> EntidadResult | None:
        """
        Proceso para buscar una entidad por número de documento.

        Returns:
            EntidadResult si existe, None si no existe
        """
        existente = await sync_to_async(self.core._buscar_por_numero_documento)(numero_documento)
        if existente is None:
            return None
        return await sync_to_async(self.core._to_result)(existente)

    async def _proceso_obtener_municipalidades(self):
        """
        Proceso para obtener todas las municipalidades activas.

        Returns:
            Lista de municipalidades activas
        """
        return await sync_to_async(self.core._obtener_municipalidades)()
