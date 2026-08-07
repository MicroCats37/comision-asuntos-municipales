"""
Reniec Results — DTOs de salida para datos de personas RENIEC.

NOTA: Stub mínimo — el archivo original fue eliminado en el purge.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReniecPersonaResult:
    """Resultado de consulta RENIEC para una persona."""
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    ubigeo: Optional[str] = None
    direccion: Optional[str] = None
