"""
Presentation schemas — Esquemas HTTP para Inspección de Obra.

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
# Schema de entrada — Inspección de Obra (duplicado para evitar acoplamiento)
# =============================================================================


class CrearLiquidacionInspeccionObraIn(BaseSchema):
    """
    Payload para crear primera revisión de Inspección Municipal de Obra.

    El tipo de liquidación se asigna automáticamente como INSPECCION_OBRA.
    El cálculo usa LiquidacionPorCategoriaVisitas (visitas por costo con mínimos).

    La categoría es requerida para resolver la tarifa correcta vía ReglaTarifaInspeccionObra.
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
    cantidad_visitas: int = Field(
        ...,
        ge=1,
        description="Cantidad de visitas de inspección realizadas o programadas (mínimo 1).",
    )
    categoria: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Categoría de inspección de obra: A, B, C, etc. Se usa para resolver la tarifa.",
    )
    expediente: Optional[str] = Field(None, description="Número de expediente (opcional)")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    # Tarifas IDs: array de exactamente 1 elemento (validación en orquestador)
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a aplicar. Para esta fase debe ser exactamente 1.",
    )
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la liquidacion",
    )


class CrearLiquidacionInspeccionObraWrapperIn(BaseSchema):
    """Wrapper para crear Inspección de Obra — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionInspeccionObraIn


# =============================================================================
# Schemas de salida — cálculo Visitas (duplicados para evitar acoplamiento)
# =============================================================================


class TarifaVisitasOut(BaseSchema):
    """Tarifa de visitas en respuesta."""

    id: uuid.UUID
    costo_por_visita: float
    visitas_minimas: int


class LiquidacionVisitasCalculoOut(BaseSchema):
    """Datos del cálculo por visitas en respuesta."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: float
    categoria: str
    tarifa: TarifaVisitasOut


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
# Schema de salida — Inspección de Obra (sin base clase acoplada)
# =============================================================================


class LiquidacionInspeccionObraOut(BaseSchema):
    """Respuesta completa de creación de Inspección de Obra."""

    liquidacion: LiquidacionOut
    tipo_liquidacion: str
    tramite_accion: str
    calculo_m2: None = None  # No aplica para inspección de obra
    calculo_visitas: Optional[LiquidacionVisitasCalculoOut] = None
    totales: TotalesOut


# =============================================================================
# Cotización schemas de salida (Inspección de Obra)
# =============================================================================


class CotizacionVisitasRevisionOut(BaseSchema):
    """Revisión de visitas en respuesta de cotización."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: float
    categoria: str
    tarifa: TarifaVisitasOut


class CotizacionVisitasMetadataOut(BaseSchema):
    """Metadata adicional en respuesta de cotización de visitas."""

    igv_valor: float
    uit_valor: float
    cantidad_visitas: Optional[int] = None


class CotizacionVisitasQuoteOut(BaseSchema):
    """Respuesta completa de cotización por visitas sin persistencia."""

    numero_revision: int
    calculo_visitas: CotizacionVisitasRevisionOut
    totales: TotalesOut
    metadata: CotizacionVisitasMetadataOut

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
# Schema de salida — List Item IO
# =============================================================================


from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionSpecificListItemBase,
    RevisionListItemCleanOut,
    ValoresListItemOut,
)


class LiquidacionIOListItemOut(LiquidacionSpecificListItemBase):
    """
    Schema de respuesta para item de lista de Inspección de Obra.

    Hereda de LiquidacionSpecificListItemBase (limpio, sin campos de Edificación).
    Usa ValoresListItemOut completo (con IGV para IO).
    """
    valores: ValoresListItemOut
