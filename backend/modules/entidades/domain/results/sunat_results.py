"""
Sunat Results - DTOs de salida para datos de instituciones SUNAT.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SunatInstitucionResult:
    """Resultado de consulta SUNAT para una institución."""
    ruc: str
    razon_social: str
    estado: str
    nombre_comercial: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    provincia: Optional[str] = None
    distrito: Optional[str] = None
    ubigeo: Optional[str] = None
