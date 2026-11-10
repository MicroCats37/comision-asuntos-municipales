"""
Delegado Batch Schemas — API contracts for delegados vigentes y batch de liquidaciones.

Inherit from BaseSchema. Used for API input (In) and output (Out).
"""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import Field, model_validator

from core.types import BaseSchema
from modules.liquidaciones.domain.constants import DictamenRevision
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
    """
    Input item para actualizar metadata extra de una LiquidacionDelegado.

    El objetivo se identifica con `liquidacion_delegado_id` (id exacto de la
    asignación) o, en el camino legacy, con `delegado_id`. Se exige al menos uno
    de los dos.

    Semántica de campos: un campo ausente conserva el valor persistido; un
    `null` explícito lo limpia. La semántica se aplica con `model_fields_set`
    en el flujo, no aquí.
    """
    liquidacion_delegado_id: Optional[uuid.UUID] = None
    delegado_id: Optional[uuid.UUID] = None
    periodo: Optional[int] = Field(None, ge=1900, le=2100)
    mes: Optional[int] = Field(None, ge=1, le=12)
    dictamen_revision: Optional[DictamenRevision] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None
    numero_rh: Optional[str] = Field(None, max_length=50)

    @model_validator(mode="after")
    def exige_al_menos_un_discriminador(self):
        """Exige `liquidacion_delegado_id` o `delegado_id` (422 si falta ambos)."""
        if self.liquidacion_delegado_id is None and self.delegado_id is None:
            raise ValueError(
                "Se requiere 'liquidacion_delegado_id' o 'delegado_id' "
                "para identificar la asignación a actualizar"
            )
        return self


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
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None


class ReciboHonorarioDelegadoMensualOut(BaseSchema):
    """
    Cabecera del RH mensual (ReciboHonorarioDelegadoMensual) enlazado a un
    detalle de honorario.

    NO expone `imp_bruto`: ese campo no existe en el modelo del RH mensual
    (solo `sub_total` y sus derivados congelados).
    """
    id: uuid.UUID
    numero: Optional[int] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    fecha_registro: datetime
    sub_total: float
    renta_cip: float
    aporte_codemu: float
    fondo_comun: float
    neto_honorario: float


class DetalleHonorarioDelegadoOut(BaseSchema):
    """
    Detalle de honorario (RH) de una asignación, con su RH mensual enlazado.

    `recibo_mensual` es None cuando el detalle está huérfano (sin RH mensual).
    """
    id: uuid.UUID
    imp_bruto: float
    sub_total: Optional[float] = None
    renta_cip: Optional[float] = None
    aporte_codemu: Optional[float] = None
    fondo_comun: Optional[float] = None
    neto_honorario: Optional[float] = None
    recibo_mensual: Optional[ReciboHonorarioDelegadoMensualOut] = None


class LiquidacionDelegadoDetalleOut(LiquidacionDelegadoOut):
    """
    Asignación (LiquidacionDelegado) enriquecida con su detalle RH.

    Compone sobre `LiquidacionDelegadoOut` (no lo duplica) y añade la
    provenance RH y el detalle de honorario.
    """
    tipo: Optional[str] = None
    numero_rh: Optional[str] = None
    creado_por_rh: bool = False
    detalle_rh: list[DetalleHonorarioDelegadoOut] = []


class LiquidacionDelegadoDetalleResponseOut(BaseSchema):
    """Output schema para GET /liquidaciones/{id}/delegados-asignaciones."""
    liquidacion_id: uuid.UUID
    asignaciones: list[LiquidacionDelegadoDetalleOut] = []


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


class DelegadoCandidatasPaginatedOut(BaseSchema):
    """Output schema for GET /delegados/candidatas with pagination."""
    delegado: LiquidacionDelegadoDelegadoOut
    items: list[CandidataOut]
    total: int
    page: int
    page_size: int
    total_pages: int


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


class DelegadoOperacionOut(BaseSchema):
    """Output schema for a single DelegadoOperacion entry."""
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
    es_vigente: bool


class DelegadoOperatividadesOut(BaseSchema):
    """Output schema for GET /delegados/operatividades."""
    delegado_id: uuid.UUID
    cip: str
    nombre_completo: str
    operatividades: list[DelegadoOperacionOut]


# ── Especialidades Revision (catalog for RH Reparticion Estacional) ─────────────


class EspecialidadRevisionOpcionOut(BaseSchema):
    """Output schema for a single EspecialidadRevision option."""
    id: uuid.UUID
    nombre: str


class EspecialidadesRevisionOut(BaseSchema):
    """Output schema for GET /liquidaciones/especialidades-revision."""
    especialidades: list[EspecialidadRevisionOpcionOut]


# Rebuild forward refs now that DelegadoBaseOut is imported
LiquidacionDelegadoEnGeneralOut.model_rebuild()
