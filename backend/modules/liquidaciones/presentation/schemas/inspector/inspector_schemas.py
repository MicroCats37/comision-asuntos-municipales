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
    dni: Optional[str] = None
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


class EspecialidadBasicaInspectorOut(BaseSchema):
    """Output schema for especialidad basica (id + nombre) en inspectores seleccionables."""
    id: uuid.UUID
    nombre: str


class InspectorSeleccionableOut(BaseSchema):
    """
    Output schema para un inspector seleccionable en el form de creación de IO.

    Shape alineado con el alpha y el schema del frontend
    (inspector-vigente.schema.ts).
    """
    id: uuid.UUID
    nombre_completo: str
    cip: str
    especialidad: EspecialidadBasicaInspectorOut
    tipo_liquidacion: str
    categoria: Optional[str] = None
    numero_registro: str
    vigencia: Optional[str] = None
    inspector_operacion_id: uuid.UUID


class InspectoresSeleccionablesOut(BaseSchema):
    """Output schema para GET /liquidaciones/inspectores/seleccionables."""
    inspectores: list[InspectorSeleccionableOut]


class TipoLiquidacionMinimalOut(BaseSchema):
    """TipoLiquidacion minimal — codigo y nombre."""
    codigo: str
    nombre: str


class LiquidacionInspectorLiquidacionOut(BaseSchema):
    """Liquidacion summary para asignación de inspector en el selector de recibos."""
    id: uuid.UUID
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional[TipoLiquidacionMinimalOut] = None


class InspectorAsignacionInspectorOut(BaseSchema):
    """Inspector minimal para asignación en el selector de recibos."""
    id: uuid.UUID
    cip: str
    dni: Optional[str] = None
    nombre_completo: str


class EspecialidadRevisionInspectorOut(BaseSchema):
    """EspecialidadRevision minimal para asignación de inspector."""
    id: uuid.UUID
    nombre: str


class LiquidacionInspectorAsignacionOut(BaseSchema):
    """Output schema para una asociación LiquidacionInspector (selector de recibos)."""
    id: uuid.UUID
    liquidacion_id: uuid.UUID
    inspector_id: uuid.UUID
    especialidad_revision: Optional[EspecialidadRevisionInspectorOut] = None
    liquidacion: Optional[LiquidacionInspectorLiquidacionOut] = None
    inspector: Optional[InspectorAsignacionInspectorOut] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None
