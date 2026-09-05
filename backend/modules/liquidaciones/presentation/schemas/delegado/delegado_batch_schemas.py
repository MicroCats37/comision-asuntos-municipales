"""
Delegado Batch Schemas — API contracts for delegados vigentes y batch de liquidaciones.

Inherit from BaseSchema. Used for API input (In) and output (Out).
"""
import uuid
from datetime import date
from typing import Optional

from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.delegado.delegado_schemas import DelegadoBaseOut


class EspecialidadRevisionOut(BaseSchema):
    """Output schema for EspecialidadRevision (anidada en delegado / asociación)."""
    id: uuid.UUID
    nombre: str


class DelegadoVigenteOut(BaseSchema):
    """
    Output schema for a delegado vigente (match municipalidad + especialidad vigente).
    Fields mirror DelegadoBaseOut (id, nombre_completo, cip, tipo, especialidad).
    DelegadoBaseOut is used in LiquidacionDelegadoEnGeneralOut; this schema
    is kept separate for the /delegados/vigentes endpoint contract.
    """
    id: uuid.UUID
    nombre_completo: str
    cip: str
    especialidad: EspecialidadRevisionOut
    tipo: str  # TITULAR or ALTERNO


class DelegadosVigentesOut(BaseSchema):
    """Output schema for GET /delegados/vigentes."""
    delegados: list[DelegadoVigenteOut]


class LiquidacionDelegadoCreateIn(BaseSchema):
    """Input item para crear una asociación LiquidacionDelegado."""
    delegado_id: uuid.UUID


class LiquidacionDelegadoUpdateIn(BaseSchema):
    """Input item para actualizar metadata extra de una LiquidacionDelegado."""
    delegado_id: uuid.UUID
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None


class LiquidacionDelegadoDeleteIn(BaseSchema):
    """Input item para eliminar una asociación LiquidacionDelegado."""
    delegado_id: uuid.UUID


class LiquidacionDelegadoBatchIn(BaseSchema):
    """Batch payload agrupado para PATCH /liquidaciones/{id}/delegados."""
    create: list[LiquidacionDelegadoCreateIn] = []
    update: list[LiquidacionDelegadoUpdateIn] = []
    delete: list[LiquidacionDelegadoDeleteIn] = []


class TipoLiquidacionMinimalOut(BaseSchema):
    """TipoLiquidacion minimal — codigo y nombre."""
    codigo: str
    nombre: str


class LiquidacionDelegadoLiquidacionOut(BaseSchema):
    """Liquidacion summary for nested output in LiquidacionDelegadoOut."""
    id: uuid.UUID
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional[TipoLiquidacionMinimalOut] = None


class LiquidacionDelegadoDelegadoOut(BaseSchema):
    """Delegado minimal for nested output in LiquidacionDelegadoOut."""
    id: uuid.UUID
    cip: str
    dni: str
    nombre_completo: str


class LiquidacionDelegadoOut(BaseSchema):
    """Output schema para una asociación LiquidacionDelegado."""
    id: uuid.UUID
    liquidacion_id: uuid.UUID
    delegado_id: uuid.UUID
    especialidad_revision: EspecialidadRevisionOut
    liquidacion: Optional[LiquidacionDelegadoLiquidacionOut] = None
    delegado: Optional[LiquidacionDelegadoDelegadoOut] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class ComprobanteActivoMinimalOut(BaseSchema):
    """Output schema for minimal active comprobante (tipo, serie, numero, fecha_emision)."""
    tipo_comprobante: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    fecha_emision: Optional[str] = None


class CandidataOut(BaseSchema):
    """Output schema for a candidate liquidacion."""
    id: uuid.UUID
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional[TipoLiquidacionMinimalOut] = None
    especialidad_candidata: EspecialidadRevisionOut
    tipo_delegado: str  # TITULAR or ALTERNO
    delegado_operacion_id: uuid.UUID  # ID of the DelegadoOperacion this candidate belongs to
    liquidacion_especifica_numero: Optional[int] = None  # numero from specific model (Edificacion, HU, etc.)
    comprobante_activo: Optional[ComprobanteActivoMinimalOut] = None  # activo=True comprobante


class DelegadoCandidatasOut(BaseSchema):
    """Output schema for GET /delegados-candidatas."""
    delegado: LiquidacionDelegadoDelegadoOut
    candidatas: list[CandidataOut]
    total: int


class LiquidacionDelegadoBatchOut(BaseSchema):
    """Output schema agrupado para PATCH /liquidaciones/{id}/delegados."""
    created: list[LiquidacionDelegadoOut] = []
    updated: list[LiquidacionDelegadoOut] = []
    deleted: list[str] = []


# --- LiquidacionDelegadoEnGeneral schemas (for LiquidacionGeneralOutput.delegados) ---


class LiquidacionDelegadoDatosOut(BaseSchema):
    """
    Assignment metadata for a LiquidacionDelegado inside LiquidacionGeneralOutput.
    Contains the mutable fields from the association (periodo, mes, dictamen, fechas).
    """
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class LiquidacionDelegadoEnGeneralOut(BaseSchema):
    """
    Output schema for a LiquidacionDelegado nested inside LiquidacionGeneralOutput.
    Shape: { datos: LiquidacionDelegadoDatosOut, delegado: DelegadoBaseOut }

    This is the canonical shape for 'delegados' in LiquidacionGeneralOutput.
    """
    datos: LiquidacionDelegadoDatosOut
    delegado: "DelegadoBaseOut"


class TipoLiquidacionListItem(BaseSchema):
    """Minimal TipoLiquidacion item for select lists."""
    id: uuid.UUID
    codigo: str
    nombre: str


class DelegadoTiposLiquidacionOut(BaseSchema):
    """Output schema for GET /delegados/tipos-liquidacion."""
    tipos: list[TipoLiquidacionListItem]


class DelegadoOperacionVigenteOut(BaseSchema):
    """Output schema for a single DelegadoOperacion vigencia entry."""
    id: uuid.UUID
    municipalidad_id: uuid.UUID
    municipalidad_nombre: str
    tipo_liquidacion_id: Optional[uuid.UUID] = None
    tipo_liquidacion_codigo: Optional[str] = None
    tipo_liquidacion_nombre: Optional[str] = None
    especialidad_id: uuid.UUID
    especialidad_nombre: str
    tipo: str  # TITULAR or ALTERNO
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None


class DelegadoOperatividadesVigentesOut(BaseSchema):
    """Output schema for GET /delegados/operatividades-vigentes."""
    delegado_id: uuid.UUID
    cip: str
    nombre_completo: str
    operatividades: list[DelegadoOperacionVigenteOut]


# Rebuild forward refs now that DelegadoBaseOut is imported
LiquidacionDelegadoEnGeneralOut.model_rebuild()
