"""
Inspector Domain Results — Internal DTOs for Orchestrator → Presenter.

NO ORM imports. Pure Pydantic BaseModel domain objects.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date


class PerfilIngenieroResult(BaseModel):
    """Domain DTO for ingeniero profile info."""
    id: str
    cip: str
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    nombre_completo: str
    correo_personal: Optional[str] = None
    correo_institucional: Optional[str] = None


class InspectorResult(BaseModel):
    """Domain DTO for a basic Inspector (list item)."""
    id: str
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroResult


class InspectorListResult(BaseModel):
    """Domain DTO for paginated Inspector list."""
    items: list[InspectorResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class InspectorDetailResult(BaseModel):
    """Domain DTO for Inspector detail (single inspector)."""
    id: str
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroResult


class InspectorVigenteResult(BaseModel):
    """Domain DTO for an Inspector with vigente status."""
    id: str
    tipo_liquidacion: str
    numero_registro: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroResult
    es_vigente: bool


class InspectorVigenteListResult(BaseModel):
    """Domain DTO for paginated list of vigentes Inspectores."""
    items: list[InspectorVigenteResult]
    total: int
    page: int
    page_size: int
    total_pages: int
