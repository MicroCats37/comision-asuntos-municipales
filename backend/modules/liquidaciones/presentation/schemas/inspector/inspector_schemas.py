"""
Inspector Schemas — API output contracts.

Inherit from BaseSchema. Used for API responses.
"""
from core.types import BaseSchema
from typing import Optional
import uuid


class PerfilIngenieroOut(BaseSchema):
    """Output schema for ingeniero profile info."""
    id: uuid.UUID
    cip: str
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    nombre_completo: str
    correo_personal: Optional[str] = None
    correo_institucional: Optional[str] = None


class InspectorOut(BaseSchema):
    """Output schema for a basic Inspector (list item)."""
    id: uuid.UUID
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroOut


class InspectorListOut(BaseSchema):
    """Output schema for paginated Inspector list."""
    items: list[InspectorOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class InspectorDetailOut(BaseSchema):
    """Output schema for Inspector detail (single inspector)."""
    id: uuid.UUID
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroOut


class InspectorVigenteOut(BaseSchema):
    """Output schema for an Inspector with vigente status."""
    id: uuid.UUID
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroOut
    es_vigente: bool


class InspectorVigenteListOut(BaseSchema):
    """Output schema for paginated list of vigentes Inspectores."""
    items: list[InspectorVigenteOut]
    total: int
    page: int
    page_size: int
    total_pages: int
