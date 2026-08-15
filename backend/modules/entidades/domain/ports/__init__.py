"""
Domain Ports — Interfaces para clientes externos.

Puerto unificado para consulta de datos de instituciones (SUNAT) y personas (RENIEC).
"""

from abc import ABC, abstractmethod

from ..results.consulta_results import ConsultaDocumentoResult


class IConsultaExternaClient(ABC):
    """
    Puerto unificado para consulta de documento por número (DNI o RUC).

    Auto-detecta el tipo por longitud: 8=DNI, 11=RUC.
    """

    @abstractmethod
    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Obtiene datos por DNI (8 dígitos) o RUC (11 dígitos).

        Args:
            documento: Número de documento (8 o 11 dígitos).

        Returns:
            ConsultaDocumentoResult con tipo_documento, numero_documento, razon_social.

        Raises:
            SunatNotFoundError: Si el RUC no existe (longitud 11).
            ReniecNotFoundError: Si el DNI no existe (longitud 8).
        """
        ...