"""
FinanzasOrchestrator — fachada asíncrona ligera para controladores.

Solo delega al ORM. Sin lógica de negocio aquí.
"""
from injector import inject

from modules.finanzas.domain.models import IGV, UIT
from modules.finanzas.domain.schemas import VariablesVigentesResult


class FinanzasOrchestrator:
    """
    Fachada asíncrona — obtiene variables vigentes desde el ORM.

    Inyecta dependencias vía __init__.
    """

    @inject
    def __init__(self):
        pass

    async def obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Obtiene las variables financieras vigentes (IGV y UIT).

        Busca el IGV y UIT activos (periodo_fin__isnull=True) más recientes.

        Returns:
            VariablesVigentesResult con los valores vigentes
        """
        igv = IGV.objects.vigente()
        uit = UIT.objects.vigente()
        return VariablesVigentesResult.from_igv_uit(igv, uit)
