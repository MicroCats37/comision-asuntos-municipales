"""
Presentation schemas — Esquemas HTTP para Entidades.

Usa Ninja Schema para request/response.
"""
import uuid
from ninja import Field, Query
from typing import Optional
from core.types import BaseSchema


class EntidadInstitucionIn(BaseSchema):
    """Payload para crear/upsert entidad tipo institución (RUC)."""
    tipo_documento: str = Field("RUC", description="Tipo de documento: RUC para instituciones")
    numero_documento: str = Field(..., min_length=11, max_length=11, description="RUC (11 dígitos)")
    razon_social: str = Field(..., min_length=1, max_length=255, description="Razón social")
    nombre_comercial: Optional[str] = Field(None, max_length=255, description="Nombre comercial")
    direccion: Optional[str] = Field(None, max_length=255, description="Dirección")


class EntidadPersonaNaturalIn(BaseSchema):
    """Payload para crear/upsert entidad tipo persona natural (DNI)."""
    tipo_documento: str = Field("DNI", description="Tipo de documento: DNI para personas naturales")
    numero_documento: str = Field(..., min_length=8, max_length=8, description="DNI (8 dígitos)")
    razon_social: str = Field(..., min_length=1, max_length=255, description="Nombre completo (nombres + apellidos)")
    direccion: Optional[str] = Field(None, max_length=255, description="Dirección")


class EntidadOut(BaseSchema):
    """Entidad en respuesta."""
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str]
    nombre_completo: str
    direccion: Optional[str]


class EntidadUpsertResponseOut(BaseSchema):
    """Respuesta de crear/upsert entidad."""
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str]
    nombre_completo: str
    direccion: Optional[str]
    creado: bool  # True si se creó, False si se actualizó


# ── Ubigeo Schemas ──────────────────────────────────────────────────────────────

class UbigeoDepartamentoOut(BaseSchema):
    """Departamento en respuesta de ubigeo."""
    id: uuid.UUID
    nombre: str


class UbigeoProvinciaBasicOut(BaseSchema):
    """Provincia en respuesta de ubigeo (sin departamento anidado)."""
    id: uuid.UUID
    nombre: str


class UbigeoProvinciaOut(BaseSchema):
    """Provincia en respuesta de ubigeo."""
    id: uuid.UUID
    nombre: str
    departamento: UbigeoDepartamentoOut


class UbigeoDistritoOut(BaseSchema):
    """Distrito en respuesta de ubigeo (formato plano y legible)."""
    id: uuid.UUID
    nombre: str
    ubigeo: str
    provincia: UbigeoProvinciaBasicOut
    departamento: UbigeoDepartamentoOut


class DistritosResponseOut(BaseSchema):
    """Respuesta de lista de distritos."""
    items: list[UbigeoDistritoOut]
    total: int


class ProvinciaBasicOut(BaseSchema):
    """Provincia básica para anidamiento en respuestas."""
    id: uuid.UUID
    nombre: str


class DistritoBasicOut(BaseSchema):
    """Distrito básico para anidamiento en respuestas."""
    id: uuid.UUID
    nombre: str


class MunicipalidadesResponseOut(BaseSchema):
    """Municipalidad en respuesta para selector."""
    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None
    provincia: Optional[ProvinciaBasicOut] = None
    distrito: Optional[DistritoBasicOut] = None


# ── Consulta Externa Schemas ──────────────────────────────────────────────────

from .consulta_schemas import InstitucionSunatOut, PersonaReniecOut
