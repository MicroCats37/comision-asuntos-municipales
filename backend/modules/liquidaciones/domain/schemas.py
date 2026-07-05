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
    """
    Datos de una revisión de edificación.

    Una revisión puede cubrir múltiples especialidades (M2M).
    El campo `especialidad` (singular) se conserva por compatibilidad con el
   API response/presenter — contiene la primera especialidad.
    El campo `especialidades` (plural) contiene TODAS las especialidades M2M
    y se usa para validación y lógica de negocio.
    """
    id: uuid.UUID
    especialidad: EspecialidadData
    especialidades: Optional[list[EspecialidadData]] = None  # Todas las M2M
    tarifa: TarifaEdificacionData
    porcentaje_liquidacion: Decimal
    habilitada: bool
    numero_revision: Optional[int] = None


class LiquidacionEdificacionesResult(BaseModel):
    """
    DTO interno de dominio para armar el resultado de una liquidación de edificaciones.

    Es un DTO de ensamblaje plano (todos los campos a nivel raíz) que el Presenter
    recibe y transforma al schema HTTP ``LiquidacionEdificacionOut``, el cual SÍ tiene
    objetos anidados para ``proyecto``, ``entidad``, ``municipalidad``, ``valores``,
    ``proyectistas``, ``delegados``, ``contactos`` y ``revisiones``.

    Campos:
        id, public_id, estado, fecha_registro, expediente, observacion,
        numero_revision, tipo_tramite, tramite_accion,
        entidad_* (nested flat), proyecto_* (nested flat), municipalidad_* (nested flat),
        proyectistas, delegados, contactos, revisiones,
        subtotal, igv, total, total_a_pagar
    """
    # ── Campos scalar (nivel raíz) ──────────────────────────────────────────────
    id: uuid.UUID  # liquidacion_id
    public_id: str  # liquidacion_public_id
    estado: str
    fecha_registro: str  # fecha_creacion renombrado
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    numero_revision: int
    tipo_tramite: str  # edificaciones_tipo_tramite
    tramite_accion: str  # edificaciones_tramite_accion
    # ── Campos anidados (construidos en builder desde datos related) ────────────
    # Entidad (nested)
    entidad_id: Optional[uuid.UUID] = None
    entidad_tipo: Optional[str] = None
    entidad_nombre: Optional[str] = None
    entidad_ruc: Optional[str] = None
    # Proyecto (nested) — campos sueltos que el presenter combina
    proyecto_id: Optional[uuid.UUID] = None
    proyecto_public_id: Optional[str] = None
    proyecto_nombre: Optional[str] = None
    proyecto_direccion: Optional[str] = None
    # Municipalidad (nested)
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # ── Listas ─────────────────────────────────────────────────────────────────
    proyectistas: list = Field(default_factory=list)  # ProyectistaEdificacionData
    delegados: list = Field(default_factory=list)  # DelegadoEdificacionData
    contactos: list = Field(default_factory=list)  # ContactoData (nuevos en Phase 2)
    revisiones: list[EdificacionRevisionData] = Field(default_factory=list)
    # ── Campos financieros directos (también van en valores nested) ──────────────
    subtotal: Decimal  # totales_subtotal
    igv: Decimal  # totales_igv
    total: Decimal  # totales_total_liquidacion
    total_a_pagar: Decimal  # totales_total_a_pagar
    # ── Variables financieras (para reference nomás) ────────────────────────────
    igv_valor: Decimal
    uit_valor: Decimal
    valor_proyecto: Decimal


class NuevaRevisionFormularioResult(BaseModel):
    """Datos para preparar formulario de nueva revisión."""
    liquidacion_previa_id: uuid.UUID
    numero_revision: int
    cobra: bool
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    valor_proyecto: Decimal
    valor_base_calculo: Decimal
    revisiones_vigentes: "list[RevisionVigenteResult]"
    proyectistas_actuales: list = Field(default_factory=list)  # list of ProyectistaEdificacionData
    tipo_tramite: str  # Tipo de trámite de la liquidación previa


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
# Proyectista y Delegado para resultados de edificaciones
# =============================================================================

class ProyectistaEdificacionData(BaseModel):
    """Proyectista anidado dentro de edificaciones en LiquidacionEdificacionesResult.

    NOTE: Actualizado para usar PerfilIngeniero referenciado.
    """
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None


class DelegadoEdificacionData(BaseModel):
    """Delegado anidado dentro de edificaciones en LiquidacionEdificacionesResult."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo: Optional[str] = None


# =============================================================================
# Proyectista inline DTO — para flujo de crear/actualizar revisions con CIP
# =============================================================================

class ProyectistaInlineData(BaseModel):
    """
    DTO para proyectistas inline con validación CIP.

    Se usa en _proceso_primera_revision y _proceso_nueva_revision para pasar
    datos de proyectistas validados al flujo. Reemplaza el uso de list[dict].

    Args:
        cip: Número de CIP del ingeniero (6 dígitos, normalizado)
        especialidad_id: ID de la especialidad (UUID)
        descripcion: Descripción opcional del proyectista
    """
    cip: str
    especialidad_id: uuid.UUID
    descripcion: Optional[str] = None


class ContactoInlineData(BaseModel):
    """DTO para crear contactos inline asociados a una liquidacion."""

    nombres: str
    apellidos: str
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    principal: bool = False
    descripcion: Optional[str] = None


class ContactoData(BaseModel):
    """Datos de contacto para resultado de liquidación de edificaciones."""
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


# =============================================================================
# Revision vigentes DTO — para obtener_revisiones_vigentes
# =============================================================================

class EspecialidadBasicaResult(BaseModel):
    """Datos básicos de una especialidad para resultados de revisiones vigentes."""
    id: uuid.UUID
    nombre: str


class RevisionVigenteResult(BaseModel):
    """
    Resultado de una revisión vigente para formulario de revisión.

    NOTE: especialidades es M2M — una revisión puede cubrir múltiples especialidades.
    Se devuelve la lista completa para que el frontend muestre todas.
    """
    id: uuid.UUID
    especialidades: list[EspecialidadBasicaResult]
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
    especialidad: str  # Keep for backward compat — first especialidad name
    especialidades: list[EspecialidadBasicaResult]  # All M2M especialidades
    tarifa: TarifaCalculoData
    monto_base: Decimal
    cobra: bool
    derecho: Decimal


# =============================================================================
# Cotización / Quote DTO — resultado de cálculo sin persistencia
# =============================================================================

class CotizacionRevisionData(BaseModel):
    """Resultado de cálculo de una revisión individual en cotización."""
    id: uuid.UUID
    especialidades: list[EspecialidadBasicaResult]  # Plural: todas las especialidades M2M
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
    valor_base_calculo: Decimal


class CotizacionQuoteData(BaseModel):
    """Resultado completo de cotización — sin persistencia en BD."""
    numero_revision: int
    revisiones: list[CotizacionRevisionData]
    totales: CotizacionTotalesData
    metadata: CotizacionMetadataData  # Internal name (no underscore to avoid Pydantic private field)


# =============================================================================
# Revision con tarifa DTO — para transformar RevisionVigenteResult flat
# a estructura anidada esperada por _calcular_revisiones
# =============================================================================

class RevisionConTarifaData(BaseModel):
    """
    Wrapper que transforma RevisionVigenteResult (flat) en estructura con
    .tarifa y .especialidad anidados para reutilización en cálculo.

    Reemplaza el helper _to_revision_calculo_data con fake inline class.
    """
    id: uuid.UUID
    porcentaje_liquidacion: Decimal
    tarifa: TarifaCalculoData
    especialidad_nombre: str


# =============================================================================
# Delegados Vigentes DTO — para flujo deObtenerDelegadosVigentes
# =============================================================================

class DelegadoVigenteResult(BaseModel):
    """Resultado de un delegado vigente para selection en formulario."""
    id: uuid.UUID
    nombre_completo: str
    cip: str
    especialidad: EspecialidadBasicaResult
    tipo: str


class DelegadosVigentesResult(BaseModel):
    """Wrapper para lista de delegados vigentes."""
    delegados: list[DelegadoVigenteResult]


# =============================================================================
# General Liquidation DTOs — para LiquidacionGeneralController (Phase 4)
# =============================================================================


class LiquidacionGeneralListItem(BaseModel):
    """
    Item de lista paginada para liquidaciones generales.

    Incluye campos comunes a todos los tipos de liquidación.
    """
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str  # Slug format: habilitacion-urbana, inspeccion-obra, etc.
    numero_revision: int
    proyecto_denominacion: str
    proyecto_public_id: str
    fecha_registro: str
    total: float
    # Campos adicionales para frontend no-edificación
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # valor_caracteristico: área para M2, cantidad_visitas para IO (None para edificaciones)
    valor_caracteristico: Optional[float] = None
    # Campos financieros para construir totales anidados
    subtotal: Optional[float] = None
    igv: Optional[float] = None
    total_a_pagar: Optional[float] = None


class LiquidacionGeneralPaginatedResult(BaseModel):
    """Resultado paginado para listado de liquidaciones generales."""
    items: list[LiquidacionGeneralListItem]
    total: int


class LiquidacionGeneralResult(BaseModel):
    """
    DTO interno para detalle de una liquidación general.

    Incluye campos comunes a todos los tipos de liquidación
    más información específica del proyecto.
    """
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str
    numero_revision: int
    fecha_registro: str
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    # Entidad
    entidad_id: Optional[uuid.UUID] = None
    entidad_tipo: Optional[str] = None
    entidad_nombre: Optional[str] = None
    entidad_ruc: Optional[str] = None
    # Proyecto
    proyecto_id: Optional[uuid.UUID] = None
    proyecto_public_id: Optional[str] = None
    proyecto_nombre: Optional[str] = None
    proyecto_direccion: Optional[str] = None
    # Municipalidad
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # Campos financieros
    subtotal: Optional[Decimal] = None
    igv: Optional[Decimal] = None
    total: Optional[Decimal] = None
    total_a_pagar: Optional[Decimal] = None
