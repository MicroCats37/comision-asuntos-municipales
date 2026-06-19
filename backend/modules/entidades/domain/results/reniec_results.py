"""
Domain Results — DTOs de salida de servicios externos (RENIEC).
"""

from pydantic import BaseModel
from datetime import date
from typing import Optional


class ReniecPersonaResult(BaseModel):
    """
    Resultado de consulta RENIEC para una persona.

    Datos crudos devueltos por el servicio externo.
    """
    dni: str
    nombres: str
    apellidos: str
    nombre_completo: str
    genero: Optional[str] = None  # "M" o "F"
    fecha_nacimiento: Optional[date] = None
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None