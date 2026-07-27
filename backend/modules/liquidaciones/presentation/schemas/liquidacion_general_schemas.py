"""
Presentation schemas — Esquemas HTTP para Liquidaciones General.
 
Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
"""
import uuid
from ninja import Field
from typing import Optional, Literal
from pydantic import ConfigDict
from core.types import BaseSchema


class EspecialidadBasicaOut(BaseSchema):
    """Especialidad básica para catálogo de especialidades vigentes."""
    id: uuid.UUID
    nombre: str


class EspecialidadesCatalogoOut(BaseSchema):
    """Respuesta de catálogo de especialidades vigentes filtradas por tipo_liquidacion."""
    items: list[EspecialidadBasicaOut] = Field(
        default_factory=list,
        description="Lista de especialidades vigentes para el tipo de liquidación dado"
    )


# ── Schemas para detalle general (LiquidacionGeneralOut) ──────────────────────

class ProyectoGeneralOut(BaseSchema):
    """Proyecto básico para respuesta general."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str] = None


class EntidadGeneralOut(BaseSchema):
    """Entidad básica para respuesta general."""
    id: Optional[uuid.UUID] = None
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    ruc: Optional[str] = None


class LiquidacionGeneralOut(BaseSchema):
    """
    Schema HTTP de respuesta para endpoints de lectura general de liquidaciones.

    Estructura plana con campos comunes a todos los tipos de liquidación.

    Campos:
        id, public_id, estado, tipo_liquidacion, numero_revision,
        fecha_registro, expediente, observacion,
        proyecto, entidad, municipalidad_nombre,
        subtotal, igv, total, total_a_pagar
    """
    model_config = ConfigDict(extra='allow')

    # ── Campos scalar ────────────────────────────────────────────────────────
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str
    numero_revision: int
    fecha_registro: str
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    municipalidad_nombre: Optional[str] = None
    # ── Campos anidados ─────────────────────────────────────────────────────
    proyecto: Optional[ProyectoGeneralOut] = None
    entidad: Optional[EntidadGeneralOut] = None
    # ── Campos financieros ──────────────────────────────────────────────────────
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


# ── Schemas para listado rico (LiquidacionGeneralListItemOut) ─────────────────

class EntidadListItemOut(BaseSchema):
    """Entidad anidada en item de lista."""
    id: Optional[uuid.UUID] = None
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    ruc: Optional[str] = None


class ProyectoListItemOut(BaseSchema):
    """Proyecto anidado en item de lista."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str] = None
    valor_proyecto: float = 0.0
    entidad: Optional[EntidadListItemOut] = None


class MunicipalidadListItemOut(BaseSchema):
    """Municipalidad anidada en item de lista."""
    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None
    provincia: Optional[str] = None
    distrito: Optional[str] = None


class ValoresListItemOut(BaseSchema):
    """Valores financieros en item de lista."""
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


class ProyectistaListItemOut(BaseSchema):
    """Proyectista en item de lista."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None


class DelegadoListItemOut(BaseSchema):
    """Delegado en item de lista."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo: Optional[str] = None


class InspectorListItemOut(BaseSchema):
    """Inspector en item de lista."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo_liquidacion: Optional[str] = None
    categoria: Optional[int] = None
    numero_registro: Optional[str] = None
    vigencia: Optional[str] = None


class ContactoListItemOut(BaseSchema):
    """Contacto en item de lista."""
    id: uuid.UUID
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    principal: bool = False
    descripcion: Optional[str] = None


class TarifaRevisionOut(BaseSchema):
    """Tarifa dentro de revision en item de lista.

    Contiene todos los campos de cálculo tipo-específicos
    (costo_m2, costo_por_visita, etc.) para que los componentes
    los lean directamente de revisiones[n].tarifa.
    """
    id: uuid.UUID
    # Common to all types
    derecho_minimo: Optional[float] = None
    derecho_maximo: Optional[float] = None
    porcentaje_minimo_uit: Optional[float] = None
    # Edificación
    porcentaje_liquidacion: Optional[float] = None
    # M2 fields (for HU, MS, IV, Taludes)
    costo_por_m2: Optional[float] = None
    area_m2: Optional[float] = None
    area_solicitada: Optional[float] = None  # User-requested area (from LiquidacionPorMetroCuadrado)
    # IO fields (for Inspeccion Obra)
    costo_por_visita: Optional[float] = None
    visitas_minimas: Optional[int] = None
    cantidad_visitas: Optional[int] = None
    categoria: Optional[str] = None


class EspecialidadRevisionOut(BaseSchema):
    """Especialidad dentro de revision."""
    id: uuid.UUID
    nombre: str


class RevisionListItemOut(BaseSchema):
    """Revision en item de lista."""
    id: uuid.UUID
    especialidades: list[EspecialidadRevisionOut] = Field(default_factory=list)
    tarifa: Optional[TarifaRevisionOut] = None


# =============================================================================
# Clean base for SPECIFIC list endpoints (HU, MS, IV, IO, Taludes)
# WITHOUT: tipo_tramite, tramite_accion, expediente (Edificación-specific)
# WITHOUT: duplicate root subtotal/igv/total/total_a_pagar (use valores only)
# WITHOUT: monto_base/cobra in revisiones
# =============================================================================


class RevisionListItemCleanOut(BaseSchema):
    """Revision en item de lista — clean version sin monto_base/cobra."""
    id: uuid.UUID
    especialidades: list[EspecialidadRevisionOut] = Field(default_factory=list)
    tarifa: Optional[TarifaRevisionOut] = None
    # M2 types (HU, MS) expose area_solicitada from LiquidacionPorMetroCuadrado
    # IO/Taludes/IV leave this None
    area_solicitada: Optional[float] = None


class ValoresM2CleanOut(BaseSchema):
    """Valores financieros para M2 (HU, MS, IV, Taludes)."""
    subtotal: float
    igv: float  # 0 for M2 types
    total: float  # equals subtotal for M2 types
    total_a_pagar: float


class LiquidacionSpecificListItemBase(BaseSchema):
    """
    Base limpia para items de lista de tipos específicos (HU, MS, IV, IO, Taludes).

    Sin campos de Edificación (tipo_tramite, tramite_accion, expediente).
    Sin campos financieros duplicados al root (usar valores.subtotal, etc.).
    """
    id: uuid.UUID
    public_id: str
    tipo_liquidacion: str
    estado: str
    numero_revision: int
    fecha_registro: str
    proyecto: ProyectoListItemOut
    entidad: Optional[EntidadListItemOut] = None
    municipalidad: MunicipalidadListItemOut
    valores: ValoresListItemOut  # Will be overridden per-type (M2 vs IO)
    proyectistas: list[ProyectistaListItemOut] = Field(default_factory=list)
    delegados: list[DelegadoListItemOut] = Field(default_factory=list)
    inspectores: list[InspectorListItemOut] = Field(default_factory=list)
    contactos: list[ContactoListItemOut] = Field(default_factory=list)
    revisiones: list[RevisionListItemCleanOut] = Field(default_factory=list)


class LiquidacionGeneralListItemOut(BaseSchema):
    """
    Item de lista en respuesta paginada general.

    Estructura rica común a todos los tipos de liquidación.
    """
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str
    numero_revision: int
    fecha_registro: str
    tramite_accion: Optional[str] = None
    tipo_tramite: Optional[str] = None
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    proyecto: ProyectoListItemOut
    entidad: Optional[EntidadListItemOut] = None
    municipalidad: MunicipalidadListItemOut
    valores: ValoresListItemOut
    proyectistas: list[ProyectistaListItemOut] = Field(default_factory=list)
    delegados: list[DelegadoListItemOut] = Field(default_factory=list)
    inspectores: list[InspectorListItemOut] = Field(default_factory=list)
    contactos: list[ContactoListItemOut] = Field(default_factory=list)
    revisiones: list[RevisionListItemOut] = Field(default_factory=list)
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


# ── Delegados Vigentes ────────────────────────────────────────────────────────


class EspecialidadBasicaDelegadoOut(BaseSchema):
    """Especialidad básica para delegado vigente."""
    id: uuid.UUID
    nombre: str


class DelegadoVigenteOut(BaseSchema):
    """Delegado vigente — datos para selection en formulario."""
    id: uuid.UUID = Field(..., description="ID del delegado (UUID)")
    nombre_completo: str = Field(..., description="Nombre completo del ingeniero")
    cip: str = Field(..., description="Número de CIP del ingeniero")
    especialidad: EspecialidadBasicaDelegadoOut = Field(..., description="Especialidad del delegado")
    tipo: str = Field(..., description="Tipo de delegado: titular o alterno")


class DelegadosVigentesOut(BaseSchema):
    """Respuesta de delegados vigentes para una municipalidad."""
    delegados: list[DelegadoVigenteOut] = Field(
        default_factory=list,
        description="Lista de delegados vigentes para la municipalidad y tarifa seleccionadas"
    )


class InspectorVigenteOut(BaseSchema):
    """Inspector vigente para selección en IO."""
    id: uuid.UUID
    nombre_completo: str
    cip: str
    especialidad: Optional[EspecialidadBasicaDelegadoOut] = None
    tipo_liquidacion: str
    categoria: Optional[int] = None
    numero_registro: str
    vigencia: str


class InspectoresVigentesOut(BaseSchema):
    """Respuesta de inspectores vigentes/elegibles para una IO."""
    inspectores: list[InspectorVigenteOut] = Field(default_factory=list)
