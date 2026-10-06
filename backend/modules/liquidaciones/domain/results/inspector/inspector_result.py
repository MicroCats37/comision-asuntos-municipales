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
    dni: Optional[str] = None
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


class InspectorVigenteFormResult(BaseModel):
    """
    Domain DTO for un inspector vigente elegible en el form de creación de IO.

    Shape alineado con el alpha (InspectorVigenteResult) y el schema del
    frontend (inspector-vigente.schema.ts).
    """
    id: str
    nombre_completo: str
    cip: str
    especialidad: Optional["EspecialidadBasicaFormResult"] = None
    tipo_liquidacion: str
    categoria: Optional[str] = None
    numero_registro: str
    vigencia: Optional[str] = None
    inspector_operacion_id: str


class EspecialidadBasicaFormResult(BaseModel):
    """Domain DTO for basic especialidad info (id + nombre)."""
    id: str
    nombre: str


class InspectoresVigentesFormResult(BaseModel):
    """Domain DTO for GET /liquidaciones/inspectores/vigentes response."""
    inspectores: list[InspectorVigenteFormResult]


class LiquidacionInspectorLiquidacionMinimal(BaseModel):
    """LiquidacionGeneral summary para asignación de inspector en el selector de recibos."""
    id: str
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional["TipoLiquidacionMinimalResult"] = None


class TipoLiquidacionMinimalResult(BaseModel):
    """TipoLiquidacion minimal — codigo y nombre."""
    codigo: str
    nombre: str


class InspectorAsignacionInspectorMinimal(BaseModel):
    """Inspector + perfil minimal para asignación de inspector."""
    id: str
    cip: str
    dni: Optional[str] = None
    nombre_completo: str


class LiquidacionInspectorAsignacionResult(BaseModel):
    """Domain DTO para una asociación LiquidacionInspector (selector de recibos)."""
    id: str
    liquidacion_id: str
    inspector_id: str
    especialidad_revision: Optional["EspecialidadRevisionResult"] = None
    liquidacion: Optional[LiquidacionInspectorLiquidacionMinimal] = None
    inspector: Optional[InspectorAsignacionInspectorMinimal] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class EspecialidadRevisionResult(BaseModel):
    """Domain DTO for EspecialidadRevision (nested en inspector de asignación)."""
    id: str
    nombre: str
