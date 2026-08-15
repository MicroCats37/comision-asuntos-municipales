"""
ConsultaExternoFlujo — flujos async para consulta de datos externos (SUNAT/RENIEC).

Estos flujos consultan los servicios externos de SUNAT y RENIEC para obtener
datos de instituciones y personas respectivamente.
"""

from injector import inject

from modules.entidades.domain.ports import ISunatClient, IReniecClient
from modules.entidades.domain.results import SunatInstitucionResult, ReniecPersonaResult


class ConsultaSunatFlujo:
    """
    Flujo async para consultar datos de institución por RUC vía SUNAT.
    """

    @inject
    def __init__(self, sunat_client: ISunatClient):
        self.sunat_client = sunat_client

    async def _proceso_consulta_sunat(self, ruc: str) -> SunatInstitucionResult:
        """
        Proceso para consultar datos de institución por RUC.

        Args:
            ruc: Número de RUC (11 dígitos).

        Returns:
            SunatInstitucionResult con los datos de la institución.

        Raises:
            SunatNotFoundError: Si el RUC no existe.
        """
        return await self.sunat_client.get_institucion(ruc)


class ConsultaReniecFlujo:
    """
    Flujo async para consultar datos de persona por DNI vía RENIEC.
    """

    @inject
    def __init__(self, reniec_client: IReniecClient):
        self.reniec_client = reniec_client

    async def _proceso_consulta_reniec(self, dni: str) -> ReniecPersonaResult:
        """
        Proceso para consultar datos de persona por DNI.

        Args:
            dni: Número de DNI (8 dígitos).

        Returns:
            ReniecPersonaResult con los datos de la persona.

        Raises:
            ReniecNotFoundError: Si el DNI no existe.
        """
        return await self.reniec_client.get_persona(dni)