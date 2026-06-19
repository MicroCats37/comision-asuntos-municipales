"""
Presentation Schemas — Esquemas HTTP para consulta externa.

Schemas para consulta de datos de instituciones (SUNAT) y personas (RENIEC).
"""

from ninja import Schema, Field
from typing import Optional
from datetime import date


class InstitucionSunatOut(Schema):
    """Respuesta de consulta SUNAT para institución."""
    ruc: str = Field(..., description="Número de RUC")
    razon_social: str = Field(..., description="Razón social")
    nombre_comercial: Optional[str] = Field(None, description="Nombre comercial")
    estado: str = Field(..., description="Estado: ACTIVO, BAJA, etc.")
    tipo_contribuyente: Optional[str] = Field(None, description="Tipo de contribuyente")
    direccion: Optional[str] = Field(None, description="Dirección")
    departamento: Optional[str] = Field(None, description="Departamento")
    provincia: Optional[str] = Field(None, description="Provincia")
    distrito: Optional[str] = Field(None, description="Distrito")


class PersonaReniecOut(Schema):
    """Respuesta de consulta RENIEC para persona."""
    dni: str = Field(..., description="Número de DNI")
    nombres: str = Field(..., description="Nombres")
    apellidos: str = Field(..., description="Apellidos")
    nombre_completo: str = Field(..., description="Nombre completo")
    genero: Optional[str] = Field(None, description="Género: M o F")
    fecha_nacimiento: Optional[date] = Field(None, description="Fecha de nacimiento")
    direccion: Optional[str] = Field(None, description="Dirección")
    ubigeo: Optional[str] = Field(None, description="Ubigeo")