"""
IngenieroHabilitadoOrchestrator — fachada asíncrona ligera para controladores.

Solo delega a IngenieroHabilitadoFlujo. Sin lógica de negocio aquí.
"""
from injector import inject

from modules.usuarios.domain.services.flujos.ingeniero_habilitado_flujo import IngenieroHabilitadoFlujo
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import IngenieroHabilitadoResult


class IngenieroHabilitadoOrchestrator:
    """
    Fachada asíncrona ligera — delega lógica a Flujo.

    Inyecta flujo vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: IngenieroHabilitadoFlujo,
    ):
        self.flujo = flujo

    async def obtener_ingeniero_habilitado(
        self,
        cip: str,
    ) -> IngenieroHabilitadoResult:
        """
        Obtiene ingeniero habilitado por CIP — delega a flujo.

        Args:
            cip: Número de CIP

        Returns:
            IngenieroHabilitadoResult con datos del ingeniero y flag habilitado
        """
        return await self.flujo._proceso_obtener_ingeniero_habilitado(cip=cip)
