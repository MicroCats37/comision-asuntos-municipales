"""Domain Results — DTOs de salida de servicios externos."""

from .sunat_results import SunatInstitucionResult
from .reniec_results import ReniecPersonaResult

__all__ = ["SunatInstitucionResult", "ReniecPersonaResult"]