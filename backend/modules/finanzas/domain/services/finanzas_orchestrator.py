"""
FinanzasOrchestrator — fachada asíncrona ligera para controladores.

Solo delega al CoreService. Sin lógica de negocio aquí.
"""
from injector import inject

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import VariablesVigentesResult


class FinanzasOrchestrator:
    """
    Fachada asíncrona — obtiene variables vigentes desde el CoreService.

    Inyecta dependencias vía __init__.
    """

    @inject
    def __init__(self, finanzas_core_service: FinanzasCoreService):
        self.finanzas_core_service = finanzas_core_service

    async def obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Obtiene las variables financieras vigentes (IGV y UIT).

        Delega al FinanzasCoreService para acceder al ORM.

        Returns:
            VariablesVigentesResult con los valores vigentes
        """
        igv = self.finanzas_core_service.get_igv_vigente()
        uit = self.finanzas_core_service.get_uit_vigente()
        return VariablesVigentesResult.from_igv_uit(igv, uit)
