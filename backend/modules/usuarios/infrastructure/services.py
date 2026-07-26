"""
Infrastructure services — external integrations for usuarios module.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class CipDataError(Exception):
    """Excepción cuando el servicio CIP retorna datos inválidos o inesperados."""
    pass


class ICipClient(ABC):
    """Port/interface for CIP external service."""

    @abstractmethod
    def get_colegiado(self, cip: str) -> Optional[dict]:
        """
        Obtiene datos del colegiado por CIP.

        Args:
            cip: Número de CIP (6 dígitos normalizado)

        Returns:
            Dict con datos del colegiado o None si no se encuentra

        Raises:
            CipServiceUnavailableError: Si el servicio no está disponible
        """
        pass


class RealCipClient(ICipClient):
    """
    Implementación real del cliente CIP que llama al endpoint externo.

    Endpoint: http://172.16.93.83:9001/api/v1/colegiado/{cip}
    """

    BASE_URL = "http://172.16.93.83:9001/api/v1"
    TIMEOUT = 10.0

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = base_url or getattr(settings, 'CIP_API_BASE_URL', self.BASE_URL)
        self.timeout = timeout or getattr(settings, 'CIP_API_TIMEOUT', self.TIMEOUT)

    def get_colegiado(self, cip: str) -> Optional[dict]:
        """
        Llama al endpoint externo de CIP para obtener datos del colegiado.

        Args:
            cip: Número de CIP normalizado (6 dígitos)

        Returns:
            Dict con datos del colegiado o None si no se encuentra (404)

        Raises:
            CipServiceUnavailableError: Si el servicio no responde o falla
        """
        url = f"{self.base_url}/colegiado/{cip}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning(
                    f"CIP API returned status {response.status_code} for CIP {cip}"
                )
                from core.exceptions import CipServiceUnavailableError
                raise CipServiceUnavailableError(
                    f"CIP API returned {response.status_code} for CIP {cip}"
                )
        except httpx.TimeoutException:
            logger.warning(f"CIP API timeout for CIP {cip}")
            from core.exceptions import CipServiceUnavailableError
            raise CipServiceUnavailableError(f"CIP API timeout for CIP {cip}")
        except httpx.RequestError as e:
            logger.warning(f"CIP API request error for CIP {cip}: {e}")
            from core.exceptions import CipServiceUnavailableError
            raise CipServiceUnavailableError(f"CIP API unavailable: {e}")


class CipClientSimulator(ICipClient):
    """
    Simulador del cliente CIP para desarrollo/testing.
    Retorna datos mockeados basados en el CIP.
    """

    # Caché de datos simulados para testing
    SIMULATED_DATA = {
        "000001": {
            "cip": "000001",
            "paterno": "GUTIERREZ",
            "materno": "TORRES",
            "nombre1": "JORGE",
            "nombre2": "LUIS",
            "dni": "12345678",
            "fechaNacimiento": "1975-03-15",
            "codGenero": "M",
            "celular": "987654321",
            "correoPers": "jorge.gutierrez@example.com",
            "correoInst": "jgutierrez@cip.org.pe",
            "direccion": "AV. PRIMAVERA 1234, LIMA",
            "distritoId": "150122",
            "codCapitulo": "IV",
            "codEspecialidad": "03",
            "codConsejo": "CONSEJO NACIONAL",
            "condicion": "1",
            "ultimoPeriodoPagado": "2026-03",
            "capitulo": {
                "id": "IV",
                "descripcion": "LIMA",
                "abreviatura": "IV-LIMA",
                "grupoEnviosInst": "cip-lima@example.com",
            },
            "habilitado": True,
        },
        "000002": {
            "cip": "000002",
            "paterno": "RODRIGUEZ",
            "materno": "GOMEZ",
            "nombre1": "MARIA",
            "nombre2": "ELENA",
            "dni": "87654321",
            "fechaNacimiento": "1980-07-22",
            "codGenero": "F",
            "celular": "987654322",
            "correoPers": "maria.rodriguez@example.com",
            "correoInst": "mrodriguez@cip.org.pe",
            "direccion": "JR. LAMBAYEQUE 567, LIMA",
            "distritoId": "150101",
            "codCapitulo": "IV",
            "codEspecialidad": "01",
            "codConsejo": "CONSEJO NACIONAL",
            "condicion": "1",
            "ultimoPeriodoPagado": "2026-03",
            "capitulo": {
                "id": "IV",
                "descripcion": "LIMA",
                "abreviatura": "IV-LIMA",
                "grupoEnviosInst": "cip-lima@example.com",
            },
            "habilitado": True,
        },
        "000003": {
            "cip": "000003",
            "paterno": "PEREZ",
            "materno": "HUAMAN",
            "nombre1": "CARLOS",
            "nombre2": "ANTONIO",
            "dni": "11223344",
            "fechaNacimiento": "1965-11-30",
            "codGenero": "M",
            "celular": "987654323",
            "correoPers": "carlos.perez@example.com",
            "correoInst": "cperez@cip.org.pe",
            "direccion": "AV. AREQUIPA 890, LIMA",
            "distritoId": "150132",
            "codCapitulo": "IV",
            "codEspecialidad": "02",
            "codConsejo": "CONSEJO NACIONAL",
            "condicion": "0",
            "ultimoPeriodoPagado": "2025-12",
            "capitulo": {
                "id": "IV",
                "descripcion": "LIMA",
                "abreviatura": "IV-LIMA",
                "grupoEnviosInst": "cip-lima@example.com",
            },
            "habilitado": False,
        },
    }

    def get_colegiado(self, cip: str) -> Optional[dict]:
        """Retorna datos simulados o None para CIPs no reconocidos."""
        return self.SIMULATED_DATA.get(cip)


def get_cip_client() -> ICipClient:
    """
    Factory function para obtener el cliente CIP apropiado según settings.

    En desarrollo (DEBUG=True) usa CipClientSimulator si CIP_USE_SIMULATOR=True.
    En producción usa RealCipClient.
    """
    use_simulator = getattr(settings, 'CIP_USE_SIMULATOR', settings.DEBUG)
    if use_simulator:
        return CipClientSimulator()
    return RealCipClient()
