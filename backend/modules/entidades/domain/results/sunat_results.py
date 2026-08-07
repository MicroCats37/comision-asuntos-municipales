"""
Sunat Results — DTOs de salida para datos de instituciones SUNAT.

NOTA: Stub mínimo — el archivo original fue eliminado en el purge.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SunatInstitucionResult:
    """Resultado de consulta SUNAT para una institución."""
    ruc: str
    razon_social: str
    estado: str
    ubigeo: Optional[str] = None
    direccion: Optional[str] = None
