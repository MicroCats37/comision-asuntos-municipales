"""
Reniec Results - DTOs de salida para datos de personas RENIEC.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class ReniecPersonaResult:
    """Resultado de consulta RENIEC para una persona."""
    dni: str
    nombres: str
    apellidos: str
    nombre_completo: str
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    genero: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
