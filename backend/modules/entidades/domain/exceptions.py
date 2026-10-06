"""
Domain Exceptions — Excepciones de dominio para violaciones de reglas de negocio.

Excepciones específicas para errores de consulta a servicios externos.
"""

from core.exceptions import HttpError, NotFoundError


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


class DocumentoInvalidoError(HttpError):
    """Excepción cuando el documento tiene formato o longitud inválida (422)."""

    code: str = "DOCUMENT_INVALID"

    def __init__(
        self,
        message: str = "El documento tiene un formato o longitud inválida.",
    ):
        self.code = self.code
        super().__init__(422, message)


class ScraperFormatError(HttpError):
    """Excepción cuando el formato del portal externo cambió y no puede ser parseado (502)."""

    code: str = "SCRAPER_FORMAT_ERROR"

    def __init__(
        self,
        message: str = "El formato del portal externo cambió y no se pudo procesar la consulta.",
    ):
        self.code = self.code
        super().__init__(502, message)


class ScraperUnavailableError(HttpError):
    """Excepción cuando el servicio de consulta externa no está disponible (503)."""

    code: str = "SCRAPER_UNAVAILABLE"

    def __init__(
        self,
        message: str = "El servicio de consulta de documentos no está disponible. Intente más tarde.",
    ):
        self.code = self.code
        super().__init__(503, message)


class ScraperTimeoutError(HttpError):
    """Excepción cuando el portal externo no respondió a tiempo (504)."""

    code: str = "SCRAPER_TIMEOUT"

    def __init__(
        self,
        message: str = "El portal externo no respondió a tiempo. Intente más tarde.",
    ):
        self.code = self.code
        super().__init__(504, message)
