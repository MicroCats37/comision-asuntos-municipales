"""
ConsultaOrchestrator — fachada asíncrona ligera para consulta de datos externos.

Delega a ConsultaExternaFlujo para consultar datos de instituciones (SUNAT) y personas (RENIEC).
"""

from injector import inject

from modules.entidades.domain.results import ConsultaDocumentoResult
from modules.entidades.domain.services.flujos.consulta_externo_flujo import ConsultaExternaFlujo


class ConsultaOrchestrator:
    """
    Fachada asíncrona ligera para consulta de datos externos.

    Solo delega a los flujos correspondientes; no contiene lógica de negocio.
    """

    @inject
    def __init__(
        self,
        externa_flujo: ConsultaExternaFlujo,
    ):
        self.externa_flujo = externa_flujo

    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Consulta datos de documento por número (DNI o RUC).

        Auto-detecta: 8 dígitos → DNI (RENIEC), 11 dígitos → RUC (SUNAT).

        Args:
            documento: Número de documento (8 o 11 dígitos).

        Returns:
            ConsultaDocumentoResult con tipo_documento, numero_documento, razon_social.

        Raises:
            SunatNotFoundError: Si el RUC (11 dígitos) no existe.
            ReniecNotFoundError: Si el DNI (8 dígitos) no existe.
        """
        return await self.externa_flujo._proceso_consulta_documento(documento)
