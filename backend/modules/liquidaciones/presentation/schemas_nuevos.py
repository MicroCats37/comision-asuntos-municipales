"""
Presentation schemas — Esquemas HTTP para los nuevos formularios de liquidación.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
Contiene los schemas de entrada (In) y salida (Out) para los 5 formularios:
- Habilitación Urbana
- Mecánica de Suelos
- Impacto Vial
- Taludes
- Inspección Municipal de Obra
"""

import uuid
from ninja import Field
from typing import Optional, Any, Dict
from pydantic import model_validator, ConfigDict
from core.types import BaseSchema


# =============================================================================
# Schemas reutilizados (inline) —参照 projekt_schemas.py existente
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
# Schemas de entrada base (compartidos por los formularios M2)
# =============================================================================


class LiquidacionM2BaseIn(BaseSchema):
    """
    Base para schemas de entrada de formularios que usan cálculo por M2.

    Los 4 formularios M2 (HU, MS, IV, TAL) comparten la misma estructura
    de cálculo, diferenciándose en el tipo_liquidacion (asignado en orchestrator).
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
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la liquidacion",
    )


# =============================================================================
# Schema de entrada: Habilitación Urbana
# =============================================================================


class CrearLiquidacionHabilitacionUrbanaIn(LiquidacionM2BaseIn):
    """
    Payload para crear primera revisión de Habilitación Urbana.

    El tipo de liquidación se asigna automáticamente como HABILITACION_URBANA.
    El cálculo usa LiquidacionPorMetroCuadrado (área por costo_m2 con límites).
    """

    pass


class CrearLiquidacionHabilitacionUrbanaWrapperIn(BaseSchema):
    """Wrapper para crear Habilitación Urbana — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionHabilitacionUrbanaIn


# =============================================================================
# Schema de entrada: Mecánica de Suelos
# =============================================================================


class CrearLiquidacionMecanicaSuelosIn(LiquidacionM2BaseIn):
    """
    Payload para crear primera revisión de Mecánica de Suelos.

    El tipo de liquidación se asigna automáticamente como MECANICA_SUELOS.
    El cálculo usa LiquidacionPorMetroCuadrado (área por costo_m2 con límites).
    """

    pass


class CrearLiquidacionMecanicaSuelosWrapperIn(BaseSchema):
    """Wrapper para crear Mecánica de Suelos — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionMecanicaSuelosIn


# =============================================================================
# Schema de entrada: Impacto Vial
# =============================================================================


class CrearLiquidacionImpactoVialIn(LiquidacionM2BaseIn):
    """
    Payload para crear primera revisión de Impacto Vial.

    El tipo de liquidación se asigna automáticamente como IMPACTO_VIAL.
    El cálculo usa LiquidacionPorMetroCuadrado (área por costo_m2 con límites).
    """

    pass


class CrearLiquidacionImpactoVialWrapperIn(BaseSchema):
    """Wrapper para crear Impacto Vial — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionImpactoVialIn


# =============================================================================
# Schema de entrada: Taludes
# =============================================================================


class CrearLiquidacionTaludesIn(LiquidacionM2BaseIn):
    """
    Payload para crear primera revisión de Taludes.

    El tipo de liquidación se asigna automáticamente como TALUDES.
    El cálculo usa LiquidacionPorMetroCuadrado (área por costo_m2 con límites).
    """

    pass


class CrearLiquidacionTaludesWrapperIn(BaseSchema):
    """Wrapper para crear Taludes — acepta { liquidacion: {...} }."""

    liquidacion: CrearLiquidacionTaludesIn


# =============================================================================
# Schema de entrada: Inspección Municipal de Obra
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
# Cotización schemas de entrada
# =============================================================================


class CotizarLiquidacionM2In(BaseSchema):
    """
    Payload para cotizar liquidaciones M2 (HU, MS, IV, TAL) sin guardar en BD.

    La cotización calcula el derecho usando la tarifa resolveda por tipo_liquidacion.
    """

    tipo_liquidacion: str = Field(
        ...,
        description="Tipo de liquidación: HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL o TALUDES.",
    )
    area_solicitada: float = Field(
        ...,
        gt=0,
        description="Área solicitada en metros cuadrados.",
    )
    # Tarifas IDs: array de exactamente 1 elemento si se proporciona
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a usar en la cotización. Debe ser exactamente 1 si se proporciona.",
    )


class CotizarLiquidacionM2WrapperIn(BaseSchema):
    """Wrapper para cotizar M2 — acepta { liquidacion: {...} }."""

    liquidacion: CotizarLiquidacionM2In


class CotizarLiquidacionInspeccionObraIn(BaseSchema):
    """
    Payload para cotizar Inspección de Obra sin guardar en BD.

    La cotización calcula el derecho usando la tarifa resolveda por categoria y tramite_accion.
    """

    cantidad_visitas: int = Field(
        ...,
        ge=1,
        description="Cantidad de visitas de inspección (mínimo 1).",
    )
    categoria: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Categoría de inspección: A, B, C, etc.",
    )
    # Tarifas IDs: array de exactamente 1 elemento si se proporciona
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a usar en la cotización. Debe ser exactamente 1 si se proporciona.",
    )


class CotizarLiquidacionInspeccionObraWrapperIn(BaseSchema):
    """Wrapper para cotizar Inspección de Obra — acepta { liquidacion: {...} }."""

    liquidacion: CotizarLiquidacionInspeccionObraIn


# =============================================================================
# Schemas de salida — cálculo M2
# =============================================================================


class TarifaM2Out(BaseSchema):
    """Tarifa M2 en respuesta."""

    id: uuid.UUID
    costo_por_m2: float
    area_minima: float
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


class ProvinciaBasicSnapshotOut(BaseSchema):
    """Provincia básica para anidamiento."""

    id: uuid.UUID
    nombre: str


class DistritoBasicSnapshotOut(BaseSchema):
    """Distrito básico para anidamiento."""

    id: uuid.UUID
    nombre: str
    provincia: Optional[ProvinciaBasicSnapshotOut] = None


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


class LiquidacionNuevaBaseOut(BaseSchema):
    """Base para salida de los 5 formularios nuevos."""

    liquidacion: LiquidacionOut
    tipo_liquidacion: str
    tramite_accion: str
    calculo_m2: Optional[LiquidacionM2CalculoOut] = None
    totales: TotalesOut


class LiquidacionHabilitacionUrbanaOut(LiquidacionNuevaBaseOut):
    """Respuesta completa de creación de Habilitación Urbana."""

    pass


class LiquidacionMecanicaSuelosOut(LiquidacionNuevaBaseOut):
    """Respuesta completa de creación de Mecánica de Suelos."""

    pass


class LiquidacionImpactoVialOut(LiquidacionNuevaBaseOut):
    """Respuesta completa de creación de Impacto Vial."""

    pass


class LiquidacionTaludesOut(LiquidacionNuevaBaseOut):
    """Respuesta completa de creación de Taludes."""

    pass


# =============================================================================
# Schemas de salida — cálculo Visitas (Inspección de Obra)
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


class LiquidacionInspeccionObraOut(LiquidacionNuevaBaseOut):
    """Respuesta completa de creación de Inspección de Obra."""

    calculo_visitas: Optional[LiquidacionVisitasCalculoOut] = None
    # Override: para inspección de obra no hay calculo_m2
    calculo_m2: None = None


# =============================================================================
# Cotización schemas de salida
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
            # Convert nested models recursively to plain dicts (Pydantic v2)
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        # Safely rename metadata to _metadata
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


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
            # Convert nested models recursively to plain dicts (Pydantic v2)
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        # Safely rename metadata to _metadata
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


# =============================================================================
# Variables financieras schemas
# =============================================================================


class VariablesFinancierasOut(BaseSchema):
    """Variables financieras para mostrar en formulario."""

    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT")


# =============================================================================
# Listado schemas
# =============================================================================


class LiquidacionNuevaListItemOut(BaseSchema):
    """Item de lista en respuesta paginada."""

    id: uuid.UUID
    numero_revision: int
    estado: str
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float
    tipo_liquidacion: str


# =============================================================================
# Tarifas vigentes schemas — para GET /tarifas-vigentes de no-edificacion
# =============================================================================


class TarifaVigenteM2Out(BaseSchema):
    """Tarifa M2 vigente para selector en formulario."""

    tarifa_id: uuid.UUID = Field(..., description="ID de TarifaLiquidacionBase (úsalo en tarifas_ids del payload)")
    detalle_id: uuid.UUID = Field(..., description="ID de TarifaPorMetroCuadrado")
    costo_por_m2: float = Field(..., description="Costo por metro cuadrado (S/)")
    area_minima: float = Field(..., description="Área mínima en m² para aplicar este costo")
    derecho_minimo: float = Field(..., description="Derecho mínimo a cobrar (S/)")
    derecho_maximo: Optional[float] = Field(None, description="Derecho máximo a cobrar (S/), null = sin límite")
    habilitada: bool = Field(..., description="Si la tarifa está habilitada para uso")


class TarifasVigentesM2Out(BaseSchema):
    """Respuesta de tarifas M2 vigentes para formulario."""

    tarifas: list[TarifaVigenteM2Out]


class TarifaVigenteVisitaOut(BaseSchema):
    """Tarifa de inspección de obra vigente para selector en formulario."""

    tarifa_id: uuid.UUID = Field(..., description="ID de TarifaLiquidacionBase (úsalo en tarifas_ids del payload)")
    detalle_id: uuid.UUID = Field(..., description="ID de TarifaPorCategoriaVisitas")
    costo_por_visita: float = Field(..., description="Costo por visita (S/)")
    visitas_minimas: int = Field(..., description="Cantidad mínima de visitas para aplicar este costo")
    categoria: str = Field(..., description="Categoría de inspección: CATEGORIA_A, CATEGORIA_B, CATEGORIA_C")
    habilitada: bool = Field(..., description="Si la tarifa está habilitada para uso")


class TarifasVigentesVisitasOut(BaseSchema):
    """Respuesta de tarifas de inspección de obra vigentes para formulario."""

    tarifas: list[TarifaVigenteVisitaOut]
