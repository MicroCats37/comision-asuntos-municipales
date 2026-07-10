"""
Presentation schemas — Esquemas HTTP para Taludes.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
"""
import uuid
from typing import Optional
from ninja import Field
from pydantic import model_validator, ConfigDict
from core.types import BaseSchema


# =============================================================================
# Schemas de entrada inline (duplicados para evitar acoplamiento con schemas_especialidades)
# =============================================================================


class EntidadInlineIn(BaseSchema):
    """
    Entidad inline para crear proyecto inline.

    Se usa dentro de ProyectoInlineIn para crear o encontrar
    una Entidad por numero_documento (upsert).
    """

    tipo_documento: str = Field(
        ...,
        description="Tipo de documento: RUC o DNI",
    )
    numero_documento: str = Field(
        ...,
        min_length=1,
        description="Número de documento (RUC 11 dígitos o DNI 8 dígitos)",
    )
    razon_social: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Razón social para RUC o nombre completo para DNI",
    )


class ProyectoInlineIn(BaseSchema):
    """
    Proyecto inline para crear durante primera revisión.

    Se usa cuando el proyecto no existe y se crea en línea.
    Mutuamente excluyente con proyecto_public_id.
    """

    denominacion: str = Field(..., min_length=1, max_length=255, description="Denominación del proyecto")
    direccion: Optional[str] = Field(None, max_length=512, description="Dirección del proyecto")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (UUID)")
    nombre_propietario: str = Field(
        ...,
        max_length=255,
        description="Nombre del propietario o representante legal",
    )
    entidad: EntidadInlineIn = Field(
        ...,
        description="Entidad inline con tipo_documento, numero_documento y razon_social. Se hace upsert por numero_documento.",
    )


class ProyectistaInlineIn(BaseSchema):
    """
    Proyectista inline para crear liquidación de taludes.

    Validación:
    - Para cada item se llama al servicio CIP externo
    - Si cualquier CIP falla o no está habilitado (condicion != '1'), se rechaza TODA la operación
    """
    cip: str = Field(..., description="Número de CIP del ingeniero (6 dígitos)")
    especialidad_id: uuid.UUID = Field(..., description="ID de la especialidad (UUID)")
    descripcion: Optional[str] = Field(None, description="Descripción opcional del proyectista")


class ContactoInlineIn(BaseSchema):
    """Contacto inline para crear y asociar a una liquidacion."""

    nombres: str = Field(..., min_length=1, description="Nombres del contacto")
    apellidos: str = Field(..., min_length=1, description="Apellidos del contacto")
    dni: Optional[str] = Field(None, description="DNI del contacto")
    cargo: Optional[str] = Field(None, description="Cargo del contacto")
    telefono: Optional[str] = Field(None, description="Teléfono del contacto")
    celular: Optional[str] = Field(None, description="Celular del contacto")
    email: Optional[str] = Field(None, description="Email del contacto")
    direccion: Optional[str] = Field(None, description="Dirección del contacto")
    principal: bool = Field(False, description="Marca este contacto como principal en la liquidacion")
    descripcion: Optional[str] = Field(None, description="Notas de la relación liquidacion-contacto")


# =============================================================================
# Schema de entrada — Taludes (duplicado para evitar acoplamiento)
# =============================================================================


class CrearLiquidacionTaludesIn(BaseSchema):
    """
    Payload para crear primera revisión de Taludes.

    El tipo de liquidación se asigna automáticamente como TALUDES.
    El cálculo usa LiquidacionPorMetroCuadrado (área por costo_m2 con límites).
    """

    # XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente.
    # La validación XOR se hace en el orquestador, no aquí.
    proyecto_public_id: Optional[str] = Field(
        None,
        description="ID público del proyecto existente (ej. PROY-2026-00001). Mutuamente excluyente con proyecto_inline.",
    )
    proyecto_inline: Optional[ProyectoInlineIn] = Field(
        None,
        description="Datos del proyecto inline a crear. Mutuamente excluyente con proyecto_public_id.",
    )
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad (UUID)")
    area_solicitada: float = Field(
        ...,
        gt=0,
        description="Área solicitada en metros cuadrados para el cálculo de derecho.",
    )
    expediente: Optional[str] = Field(None, description="Número de expediente (opcional)")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    # Tarifas IDs: array de exactamente 1 elemento (validación en orquestador)
    # default=None para distinguir "no proporcionado" de "proporcionado vacío"
    # Si se proporciona y está vacío, el campo falla min_length=1 y retorna 422.
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a aplicar. Para esta fase debe ser exactamente 1.",
    )
    # NUEVO: Proyectistas inline con validación CIP (opcional)
    proyectistas: list[ProyectistaInlineIn] = Field(
        default=[],
        description="Lista de proyectistas inline con CIP. Si se provee, reemplaza completamente a proyectistas_ids."
    )
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la liquidacion",
    )


class CrearLiquidacionTaludesWrapperIn(BaseSchema):
    """Wrapper para crear Taludes — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionTaludesIn


# =============================================================================
# Schemas de salida — cálculo M2 (duplicados para evitar acoplamiento)
# =============================================================================


class TarifaM2Out(BaseSchema):
    """Tarifa M2 en respuesta."""

    id: uuid.UUID
    costo_por_m2: float
    area_m2: float
    derecho_minimo: float
    derecho_maximo: Optional[float]


class LiquidacionM2CalculoOut(BaseSchema):
    """Datos del cálculo por M2 en respuesta."""

    area_solicitada: float
    area_base_calculo: float
    derecho: float
    tarifa: TarifaM2Out


class TotalesOut(BaseSchema):
    """Totales de la liquidación."""

    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class EntidadOut(BaseSchema):
    """Entidad anidada en proyecto."""

    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]
    ruc: Optional[str]


class ProyectoOut(BaseSchema):
    """Proyecto anidado en liquidación."""

    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str]
    entidad: Optional[EntidadOut] = None


class MunicipalidadesSnapshotOut(BaseSchema):
    """Municipalidad anidada."""

    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None


class LiquidacionOut(BaseSchema):
    """Liquidación en respuesta snapshot."""

    id: uuid.UUID
    public_id: str
    estado: str
    fecha_creacion: str
    proyecto: ProyectoOut
    municipalidad: MunicipalidadesSnapshotOut
    expediente: Optional[str] = None
    observacion: Optional[str]


# =============================================================================
# Schema de salida — Taludes (sin base clase acoplada)
# =============================================================================


class LiquidacionTaludesOut(BaseSchema):
    """Respuesta completa de creación de Taludes."""

    liquidacion: LiquidacionOut
    tipo_liquidacion: str
    tramite_accion: str
    calculo_m2: Optional[LiquidacionM2CalculoOut] = None
    totales: TotalesOut


# =============================================================================
# Cotización schemas de entrada (específicos para Taludes — sin tipo_liquidacion)
# =============================================================================


class CotizarLiquidacionTaludesIn(BaseSchema):
    """
    Payload para cotizar Taludes sin guardar en BD.

    NO incluye tipo_liquidacion — el controller lo inyecta internamente.
    """

    area_solicitada: float = Field(
        ...,
        gt=0,
        description="Área solicitada en metros cuadrados.",
    )
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a usar en la cotización. Debe ser exactamente 1 si se proporciona.",
    )


class CotizarLiquidacionTaludesWrapperIn(BaseSchema):
    """Wrapper para cotizar Taludes — acepta { liquidacion: {...} } sin tipo_liquidacion."""

    liquidacion: CotizarLiquidacionTaludesIn


# =============================================================================
# Cotización schemas de salida (compartidos entre M2)
# =============================================================================


class CotizacionM2RevisionOut(BaseSchema):
    """Revisión M2 en respuesta de cotización."""

    area_solicitada: float
    area_base_calculo: float
    derecho: float
    tarifa: TarifaM2Out


class CotizacionM2MetadataOut(BaseSchema):
    """Metadata adicional en respuesta de cotización M2."""

    igv_valor: float
    uit_valor: float
    area_solicitada: Optional[float] = None


class CotizacionM2QuoteOut(BaseSchema):
    """Respuesta completa de cotización por M2 sin persistencia."""

    numero_revision: int
    calculo_m2: CotizacionM2RevisionOut
    totales: TotalesOut
    metadata: CotizacionM2MetadataOut

    @model_validator(mode="wrap")
    def serialize_model(self, handler):
        """Rename metadata to _metadata in JSON output per API contract."""
        data = handler(self)
        if hasattr(data, "model_dump"):
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


# =============================================================================
# Schema de salida — List Item Taludes
# =============================================================================


from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionSpecificListItemBase,
    RevisionListItemCleanOut,
    ValoresM2CleanOut,
)


class LiquidacionTaludesListItemOut(LiquidacionSpecificListItemBase):
    """
    Schema de respuesta para item de lista de Taludes.

    Hereda de LiquidacionSpecificListItemBase (limpio, sin campos de Edificación).
    Usa ValoresM2CleanOut (sin IGV).
    """
    valores: ValoresM2CleanOut
