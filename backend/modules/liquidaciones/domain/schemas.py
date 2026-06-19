"""
Domain schemas — DTOs internos para servicios de Liquidaciones Edificaciones.
"""
import uuid
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class VariablesFinancierasResult(BaseModel):
    """Variables financieras vigentes (IGV y UIT)."""
    igv_valor: Decimal
    igv_periodo_inicio: date
    uit_valor: Decimal
    uit_periodo_inicio: date


class TarifaEdificacionData(BaseModel):
    """Datos de una tarifa de edificación."""
    id: uuid.UUID
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal]
    porcentaje_minimo_uit: Decimal


class EspecialidadData(BaseModel):
    """Datos de una especialidad."""
    id: uuid.UUID
    nombre: str


class EdificacionRevisionData(BaseModel):
    """Datos de una revisión de edificación."""
    id: uuid.UUID
    especialidad: EspecialidadData
    tarifa: TarifaEdificacionData
    porcentaje_liquidacion: Decimal
    habilitada: bool
    numero_revision: Optional[int] = None


class LiquidacionEdificacionesResult(BaseModel):
    """Resultado completo de una liquidación de edificaciones."""
    liquidacion_id: uuid.UUID
    liquidacion_public_id: str
    numero_revision: int
    estado: str
    fecha_creacion: str
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    proyecto_direccion: Optional[str]
    proyecto_entidad_id: Optional[uuid.UUID]
    proyecto_entidad_tipo: Optional[str]
    proyecto_entidad_nombre: Optional[str]
    proyecto_entidad_ruc: Optional[str]
    municipalidad_id: uuid.UUID
    municipalidad_nombre: str
    # proyectistas ahora van en edificaciones_proyectistas, no en proyecto
    edificaciones_proyectistas: list = Field(default_factory=list)  # list of ProyectistaSnapshotData
    edificaciones_public_id: str
    edificaciones_tipo_tramite: str
    edificaciones_tramite_accion: str
    observacion: Optional[str]
    edificaciones_revisiones: list[EdificacionRevisionData]
    igv_valor: Decimal
    uit_valor: Decimal
    valor_proyecto: Decimal
    totales_subtotal: Decimal
    totales_igv: Decimal
    totales_total_liquidacion: Decimal
    totales_total_a_pagar: Decimal


class NuevaRevisionFormularioResult(BaseModel):
    """Datos para preparar formulario de nueva revisión."""
    liquidacion_previa_id: uuid.UUID
    numero_revision: int
    cobra: bool
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    valor_proyecto: Decimal
    revisiones_vigentes: list[EdificacionRevisionData]


class LiquidacionEdificacionesListItem(BaseModel):
    """Item de lista paginada de liquidaciones de edificaciones."""
    id: uuid.UUID
    numero_revision: int
    estado: str
    valor_proyecto: float
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float


class LiquidacionEdificacionesPaginatedResult(BaseModel):
    """Resultado paginado para listado de liquidaciones de edificaciones."""
    items: list[LiquidacionEdificacionesListItem]
    total: int


# =============================================================================
# Snapshot schemas — typed DTOs para el payload JSON del LiquidacionSnapshot
# =============================================================================

class TarifaSnapshotData(BaseModel):
    """Tarifa embebida dentro de RevisionSnapshotData."""
    id: uuid.UUID
    derecho_minimo: str
    derecho_maximo: Optional[str]
    porcentaje_minimo_uit: str


class RevisionSnapshotData(BaseModel):
    """Una revisión individual dentro del snapshot de edificaciones."""
    id: uuid.UUID
    numero_revision: int
    especialidad: str
    tarifa: TarifaSnapshotData
    monto_base: float
    cobra: bool
    derecho: float


class EntidadSnapshotData(BaseModel):
    """Entidad anidada dentro de ProyectoSnapshotData."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]
    ruc: Optional[str]


class ProyectistaSnapshotData(BaseModel):
    """Proyectista anidado dentro de ProyectoSnapshotData."""
    id: uuid.UUID
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]
    nombres: str
    apellidos: str


class ProyectoSnapshotData(BaseModel):
    """Proyecto anidado dentro de LiquidacionSnapshotData."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: str
    valor_proyecto: float
    entidad: Optional[EntidadSnapshotData]
    # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas


class LiquidacionSnapshotData(BaseModel):
    """Sección 'liquidacion' del snapshot completo."""
    id: uuid.UUID
    public_id: str
    numero_liquidacion: str
    estado: str
    fecha_creacion: str
    proyecto: ProyectoSnapshotData
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # expediente fue removido — ya no existe en el modelo
    observacion: str


class EdificacionesSnapshotData(BaseModel):
    """Sección 'edificaciones' del snapshot completo."""
    public_id: str
    numero_revision: int
    tipo_tramite: str
    tramite_accion: str
    proyectistas: list[ProyectistaSnapshotData] = Field(default_factory=list)
    revisiones: list[RevisionSnapshotData]


class TotalesSnapshotData(BaseModel):
    """Sección 'totales' del snapshot completo."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class MetadataSnapshotData(BaseModel):
    """Sección '_metadata' interna del snapshot."""
    igv_valor: float
    uit_valor: float
    cobra: bool


class LiquidacionSnapshotResult(BaseModel):
    """
    Schema completo del snapshot de liquidación.
    Se usa como tipo de retorno tipado en _proceso_obtener_liquidacion.
    """
    liquidacion: LiquidacionSnapshotData
    edificaciones: EdificacionesSnapshotData
    totales: TotalesSnapshotData
    _metadata: MetadataSnapshotData


# =============================================================================
# Revision vigentes DTO — para obtener_revisiones_vigentes
# =============================================================================

class RevisionVigenteResult(BaseModel):
    """Resultado de una revisión vigente para formulario de revisión."""
    id: uuid.UUID
    especialidad_id: uuid.UUID
    especialidad_nombre: str
    tarifa_id: uuid.UUID
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal]
    porcentaje_minimo_uit: Decimal
    habilitada: bool


# =============================================================================
# Intermediate calculation DTO — para resultados de cálculo de revisión
# =============================================================================

class TarifaCalculoData(BaseModel):
    """Tarifa en resultado de cálculo de revisión."""
    id: uuid.UUID
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal]
    porcentaje_minimo_uit: Decimal


class RevisionCalculoData(BaseModel):
    """
    Resultado de cálculo de una revisión individual.
    Schema intermedio usado en _build_snapshot_data y _build_result.
    """
    id: uuid.UUID
    numero_revision: int
    especialidad: str
    tarifa: TarifaCalculoData
    monto_base: Decimal
    cobra: bool
    derecho: Decimal


# =============================================================================
# Fallback snapshot result — cuando no hay snapshot guardado
# =============================================================================

class ProyectoFallbackData(BaseModel):
    """Proyecto en resultado sin snapshot."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: str
    valor_proyecto: float


class LiquidacionFallbackData(BaseModel):
    """Sección liquidacion para resultado sin snapshot."""
    id: uuid.UUID
    public_id: str
    numero_liquidacion: str
    estado: str
    fecha_creacion: str
    proyecto: ProyectoFallbackData
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # expediente fue removido
    observacion: str


class EdificacionesFallbackData(BaseModel):
    """Sección edificaciones para resultado sin snapshot (vacía)."""
    public_id: str = ""
    numero_revision: int = 0
    tipo_tramite: str = ""
    tramite_accion: str = ""
    revisiones: list


class TotalesFallbackData(BaseModel):
    """Sección totales para resultado sin snapshot (en cero)."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class LiquidacionSnapshotFallbackResult(BaseModel):
    """
    Schema para resultado sin snapshot — cuándo la liquidación existe
    pero no tiene snapshot calculado aún.
    """
    liquidacion: LiquidacionFallbackData
    edificaciones: EdificacionesFallbackData
    totales: TotalesFallbackData


# =============================================================================
# Cotización / Quote DTO — resultado de cálculo sin persistencia
# =============================================================================

class CotizacionRevisionData(BaseModel):
    """Resultado de cálculo de una revisión individual en cotización."""
    id: uuid.UUID
    especialidad: str
    tarifa: TarifaCalculoData
    monto_base: Decimal
    cobra: bool
    derecho: Decimal


class CotizacionTotalesData(BaseModel):
    """Totales en resultado de cotización."""
    subtotal: Decimal
    igv: Decimal
    total: Decimal
    liquidacion_total: Decimal
    total_a_pagar: Decimal


class CotizacionMetadataData(BaseModel):
    """Metadata adicional en resultado de cotización."""
    igv_valor: Decimal
    uit_valor: Decimal
    cobra: bool


class CotizacionQuoteData(BaseModel):
    """Resultado completo de cotización — sin persistencia en BD."""
    numero_revision: int
    revisiones: list[CotizacionRevisionData]
    totales: CotizacionTotalesData
    metadata: CotizacionMetadataData  # Internal name (no underscore to avoid Pydantic private field)
