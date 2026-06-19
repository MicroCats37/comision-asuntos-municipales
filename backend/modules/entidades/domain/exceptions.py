"""
Domain Exceptions — Excepciones de dominio para violaciones de reglas de negocio.

Excepciones específicas para errores de consulta a servicios externos.
"""

from core.exceptions import NotFoundError


class SunatNotFoundError(NotFoundError):
    """Excepción cuando un RUC no es encontrado en el servicio SUNAT (404)."""

    code: str = "SUNAT_NOT_FOUND"

    def __init__(self, ruc: str):
        self.code = self.code
        super().__init__(404, f"RUC {ruc} no encontrado en SUNAT")


class ReniecNotFoundError(NotFoundError):
    """Excepción cuando un DNI no es encontrado en el servicio RENIEC (404)."""

    code: str = "RENIEC_NOT_FOUND"

    def __init__(self, dni: str):
        self.code = self.code
        super().__init__(404, f"DNI {dni} no encontrado en RENIEC")