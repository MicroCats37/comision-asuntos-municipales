"""
Presentation schemas — Esquemas HTTP para Entidades.

Usa Ninja Schema para request/response.
"""
import uuid
from ninja import Schema, Field, Query
from typing import Optional


class EntidadInstitucionIn(Schema):
    """Payload para crear/upsert entidad tipo institución (RUC)."""
    tipo_documento: str = Field("RUC", description="Tipo de documento: RUC para instituciones")
    numero_documento: str = Field(..., min_length=11, max_length=11, description="RUC (11 dígitos)")
    razon_social: str = Field(..., min_length=1, max_length=255, description="Razón social")
    nombre_comercial: Optional[str] = Field(None, max_length=255, description="Nombre comercial")
    direccion: Optional[str] = Field(None, max_length=255, description="Dirección")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (UUID)")


class EntidadPersonaNaturalIn(Schema):
    """Payload para crear/upsert entidad tipo persona natural (DNI)."""
    tipo_documento: str = Field("DNI", description="Tipo de documento: DNI para personas naturales")
    numero_documento: str = Field(..., min_length=8, max_length=8, description="DNI (8 dígitos)")
    nombres: str = Field(..., min_length=1, max_length=255, description="Nombres")
    apellidos: str = Field(..., min_length=1, max_length=255, description="Apellidos")
    direccion: Optional[str] = Field(None, max_length=255, description="Dirección")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (UUID)")


class EntidadOut(Schema):
    """Entidad en respuesta."""
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str]
    nombres: Optional[str]
    apellidos: Optional[str]
    nombre_completo: str
    direccion: Optional[str]
    distrito_id: Optional[uuid.UUID]
    activo: bool


class EntidadUpsertResponseOut(Schema):
    """Respuesta de crear/upsert entidad."""
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str]
    nombres: Optional[str]
    apellidos: Optional[str]
    nombre_completo: str
    direccion: Optional[str]
    distrito_id: Optional[uuid.UUID]
    activo: bool
    creado: bool  # True si se creó, False si se actualizó


# ── Ubigeo Schemas ──────────────────────────────────────────────────────────────

class UbigeoDepartamentoOut(Schema):
    """Departamento en respuesta de ubigeo."""
    id: uuid.UUID
    nombre: str


class UbigeoProvinciaOut(Schema):
    """Provincia en respuesta de ubigeo."""
    id: uuid.UUID
    nombre: str
    departamento: UbigeoDepartamentoOut


class UbigeoDistritoOut(Schema):
    """Distrito en respuesta de ubigeo."""
    id: uuid.UUID
    nombre: str
    ubigeo: str
    provincia: UbigeoProvinciaOut
    departamento: UbigeoDepartamentoOut


class DistritosResponseOut(Schema):
    """Respuesta de lista de distritos."""
    items: list[UbigeoDistritoOut]
    total: int


class ProvinciaBasicOut(Schema):
    """Provincia básica para anidamiento en respuestas."""
    id: uuid.UUID
    nombre: str


class DistritoBasicOut(Schema):
    """Distrito básico para anidamiento en respuestas."""
    id: uuid.UUID
    nombre: str


class MunicipalidadesResponseOut(Schema):
    """Municipalidad en respuesta para selector."""
    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None
    provincia: Optional[ProvinciaBasicOut] = None
    distrito: Optional[DistritoBasicOut] = None


# ── Consulta Externa Schemas ──────────────────────────────────────────────────

from .consulta_schemas import InstitucionSunatOut, PersonaReniecOut
