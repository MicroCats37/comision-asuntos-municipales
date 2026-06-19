"""
EntidadesOrchestrator — fachada asíncrona ligera para controladores de entidades.
"""
import uuid
from asgiref.sync import sync_to_async
from injector import inject

from modules.entidades.domain.schemas import EntidadResult
from modules.entidades.domain.services.flujos.entidad_flujo import EntidadFlujo


class EntidadesOrchestrator:
    """
    Fachada asíncrona ligera para entidades.
    """

    @inject
    def __init__(self, flujo: EntidadFlujo):
        self.flujo = flujo

    async def upsert_entidad(
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
        Crea o actualiza una entidad.

        Returns:
            tuple: (EntidadResult, creado) donde creado=True si se creó, False si se actualizó
        """
        return await self.flujo._proceso_upsert(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            razon_social=razon_social,
            nombres=nombres,
            apellidos=apellidos,
            nombre_comercial=nombre_comercial,
            direccion=direccion,
            distrito_id=distrito_id,
        )

    async def buscar_por_documento(self, numero_documento: str) -> EntidadResult | None:
        """
        Busca una entidad por número de documento.

        Returns:
            EntidadResult si existe, None si no existe
        """
        return await self.flujo._proceso_buscar_por_documento(numero_documento)

    async def obtener_distritos(
        self,
        search: str | None = None,
        provincia_id: str | None = None,
        departamento_id: str | None = None,
    ):
        """
        Obtiene distritos con filtros opcionales.

        Args:
            search: Texto para filtrar por nombre de distrito
            provincia_id: ID de provincia para filtrar
            departamento_id: ID de departamento para filtrar

        Returns:
            Lista de distritos que cumplen los filtros
        """
        # Llama al método sync del core envuelto en sync_to_async
        return await sync_to_async(self.flujo.core._obtener_distritos)(
            search=search,
            provincia_id=provincia_id,
            departamento_id=departamento_id,
        )

    async def obtener_municipalidades(self):
        """Obtiene todas las municipalidades activas."""
        return await self.flujo._proceso_obtener_municipalidades()
