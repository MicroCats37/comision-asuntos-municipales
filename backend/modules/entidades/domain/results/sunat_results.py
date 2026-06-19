"""
Domain Results — DTOs de salida de servicios externos (SUNAT/RENIEC).

Estos schemas representan los datos crudos devueltos por los servicios externos,
antes de cualquier transformación o persistencia en nuestra base de datos.
"""

from pydantic import BaseModel
from datetime import date
from typing import Optional


class SunatInstitucionResult(BaseModel):
    """
    Resultado de consulta SUNAT para una institución.

    Datos crudos devueltos por el servicio externo.
    """
    ruc: str
    razon_social: str
    nombre_comercial: Optional[str] = None
    estado: str  # "ACTIVO", "BAJA", etc.
    tipo_contribuyente: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    provincia: Optional[str] = None
    distrito: Optional[str] = None
