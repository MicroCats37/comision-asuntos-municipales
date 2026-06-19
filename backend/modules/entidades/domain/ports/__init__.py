"""
Domain Ports — Interfaces para clientes externos.

Puerto para consulta de datos de instituciones (SUNAT) y personas (RENIEC).
"""

from abc import ABC, abstractmethod

from ..results.sunat_results import SunatInstitucionResult
from ..results.reniec_results import ReniecPersonaResult


class ISunatClient(ABC):
    """
    Puerto para obtener datos de una institución según SUNAT.

    Esta interfaz permite consultar los datos de una empresa o institución
    registrada en la SUNAT por su RUC.
    """

    @abstractmethod
    async def get_institucion(self, ruc: str) -> SunatInstitucionResult:
        """
        Obtiene los datos de una institución por RUC.

        Args:
            ruc: Número de RUC de la institución (11 dígitos).

        Returns:
            SunatInstitucionResult con los datos de la institución.

        Raises:
            SunatNotFoundError: Si el RUC no existe o no se puede consultar.
        """
        ...


class IReniecClient(ABC):
    """
    Puerto para obtener datos de una persona según RENIEC.

    Esta interfaz permite consultar los datos personales de una persona
    registrada en el RENIEC por su DNI.
    """

    @abstractmethod
    async def get_persona(self, dni: str) -> ReniecPersonaResult:
        """
        Obtiene los datos de una persona por DNI.

        Args:
            dni: Número de DNI de la persona (8 dígitos).

        Returns:
            ReniecPersonaResult con los datos de la persona.

        Raises:
            ReniecNotFoundError: Si el DNI no existe o no se puede consultar.
        """
        ...