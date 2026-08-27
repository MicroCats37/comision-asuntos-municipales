"""
Delegado Batch Schemas — API contracts for delegados vigentes y batch de liquidaciones.

Inherit from BaseSchema. Used for API input (In) and output (Out).
"""
import uuid
from datetime import date
from typing import Optional

from core.types import BaseSchema


class EspecialidadRevisionOut(BaseSchema):
    """Output schema for EspecialidadRevision (anidada en delegado / asociación)."""
    id: uuid.UUID
    nombre: str


class DelegadoVigenteOut(BaseSchema):
    """Output schema for a delegado vigente (match municipalidad + especialidad vigente)."""
    id: uuid.UUID
    nombre_completo: str
    cip: str
    especialidad: EspecialidadRevisionOut
    tipo: str


class DelegadosVigentesOut(BaseSchema):
    """Output schema for GET /delegados/vigentes."""
    delegados: list[DelegadoVigenteOut]


class LiquidacionDelegadoCreateIn(BaseSchema):
    """Input item para crear una asociación LiquidacionDelegado."""
    delegado_id: uuid.UUID


class LiquidacionDelegadoUpdateIn(BaseSchema):
    """Input item para actualizar metadata extra de una LiquidacionDelegado."""
    delegado_id: uuid.UUID
    periodo: Optional[str] = None
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
    periodo: Optional[str] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


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
