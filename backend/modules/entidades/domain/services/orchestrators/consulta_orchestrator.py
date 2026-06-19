"""
ConsultaOrchestrator — fachada asíncrona ligera para consulta de datos externos.

Delega a ConsultaSunatFlujo y ConsultaReniecFlujo para consultar
datos de instituciones (SUNAT) y personas (RENIEC).
"""

from injector import inject

from modules.entidades.domain.results import SunatInstitucionResult, ReniecPersonaResult
from modules.entidades.domain.services.flujos.consulta_externo_flujo import (
    ConsultaSunatFlujo,
    ConsultaReniecFlujo,
)


class ConsultaOrchestrator:
    """
    Fachada asíncrona ligera para consulta de datos externos.

    Solo delega a los flujos correspondientes; no contiene lógica de negocio.
    """

    @inject
    def __init__(
        self,
        sunat_flujo: ConsultaSunatFlujo,
        reniec_flujo: ConsultaReniecFlujo,
    ):
        self.sunat_flujo = sunat_flujo
        self.reniec_flujo = reniec_flujo

    async def consultar_sunat(self, ruc: str) -> SunatInstitucionResult:
        """
        Consulta datos de institución por RUC vía SUNAT.

        Args:
            ruc: Número de RUC (11 dígitos).

        Returns:
            SunatInstitucionResult con los datos de la institución.

        Raises:
            SunatNotFoundError: Si el RUC no existe.
        """
        return await self.sunat_flujo._proceso_consulta_sunat(ruc)

    async def consultar_reniec(self, dni: str) -> ReniecPersonaResult:
        """
        Consulta datos de persona por DNI vía RENIEC.

        Args:
            dni: Número de DNI (8 dígitos).

        Returns:
            ReniecPersonaResult con los datos de la persona.

        Raises:
            ReniecNotFoundError: Si el DNI no existe.
        """
        return await self.reniec_flujo._proceso_consulta_reniec(dni)