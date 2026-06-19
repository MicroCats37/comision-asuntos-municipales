"""
ProyectistaOrchestrator — fachada asíncrona ligera para controladores de proyectistas.
"""
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
        nombres: str,
        apellidos: str,
        cip: str | None,
        dni: str | None,
        cap: str | None,
    ) -> tuple[dict, bool]:
        """
        Crea o busca un proyectista.

        Returns:
            tuple: (dict con datos de proyectista, creado) donde creado=True si se creó, False si se encontró existente
        """
        result, creado = await self.flujo._proceso_upsert(
            nombres=nombres,
            apellidos=apellidos,
            cip=cip,
            dni=dni,
            cap=cap,
        )
        return result.model_dump(mode='json'), creado
