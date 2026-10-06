"""
FinanzasFlujo — flujos de negocio para finanzas.

Cada método _proceso_* es un caso de uso completo.
"""
from injector import inject

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import VariablesVigentesResult


class FinanzasFlujo:
    """
    Flujos para finanzas — _proceso_obtener_variables_vigentes.

    Inyecta FinanzasCoreService para operaciones ORM.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def _proceso_obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Flujo para obtener las variables financieras vigentes (IGV y UIT).

        1. Consulta el IGV vigente vía CoreService.
        2. Consulta la UIT vigente vía CoreService.
        3. Construye el resultado agregado.

        Returns:
            VariablesVigentesResult con los valores vigentes
        """
        igv = self.core.get_igv_vigente()
        uit = self.core.get_uit_vigente()
        return VariablesVigentesResult.from_igv_uit(igv, uit)
