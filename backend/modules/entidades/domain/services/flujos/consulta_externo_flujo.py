"""
ConsultaExternoFlujo — flujos async para consulta de datos externos (SUNAT/RENIEC).

Flujo unificado que auto-detecta tipo de documento por longitud:
- 8 dígitos → DNI (RENIEC)
- 11 dígitos → RUC (SUNAT)
"""

from injector import inject

from modules.entidades.domain.ports import IConsultaExternaClient
from modules.entidades.domain.results import ConsultaDocumentoResult


class ConsultaExternaFlujo:
    """
    Flujo async unificado para consulta de documento por número (DNI o RUC).

    Auto-detecta el tipo por longitud: 8=DNI, 11=RUC.
    """

    @inject
    def __init__(self, consulta_cliente: IConsultaExternaClient):
        self.consulta_cliente = consulta_cliente

    async def _proceso_consulta_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Proceso para consultar datos de documento por número.

        Args:
            documento: Número de documento (8 o 11 dígitos).

        Returns:
            ConsultaDocumentoResult con tipo_documento, numero_documento, razon_social.

        Raises:
            SunatNotFoundError: Si el RUC (11 dígitos) no existe.
            ReniecNotFoundError: Si el DNI (8 dígitos) no existe.
        """
        return await self.consulta_cliente.consultar_documento(documento)
