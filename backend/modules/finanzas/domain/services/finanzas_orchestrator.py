"""
FinanzasOrchestrator — fachada asíncrona ligera para controladores de finanzas.
"""
from injector import inject

from .finanzas_core_service import FinanzasCoreService


class FinanzasOrchestrator:
    """
    Fachada asíncrona ligera para finanzas.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    async def obtener_variables_vigentes(self) -> dict:
        """Obtiene variables financieras vigentes — delega a core."""
        return await self.core.obtener_variables_financieras_vigentes()
