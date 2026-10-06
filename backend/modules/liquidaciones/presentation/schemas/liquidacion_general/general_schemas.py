"""
General presentation schemas — Cabeceras y metadatos comunes a todo tipo de liquidación.
"""
from core.types import BaseSchema
from ninja import Field
from typing import Optional
import uuid
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    LiquidacionDelegadoEnGeneralOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.comprobante_schemas import (
    LiquidacionComprobanteOutput,
)

# --- Entidad & Proyecto (In/Out) ---
class EntidadInlineSchema(BaseSchema):
    tipo_documento: Optional[str] = Field(None, description="Tipo de documento (RUC/DNI)")
    numero_documento: str = Field(..., description="Número de documento")
    razon_social: str = Field(..., description="Razón social o nombres")

class ProyectoCotizarSchema(BaseSchema):
    denominacion: Optional[str] = Field(None, description="Denominación del proyecto (opcional)")
    nombre_propietario: str = Field(..., description="Nombre del propietario")
    direccion: str = Field(..., description="Dirección del proyecto")
    urbanizacion: Optional[str] = Field(None, description="Urbanización o habilitación urbana del proyecto")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (opcional, nullable en ORM)")
    entidad: EntidadInlineSchema = Field(..., description="Entidad propietaria")

class DepartamentoOutput(BaseSchema):
    """Departamento del distrito."""
    id: uuid.UUID = Field(..., description="ID del departamento")
    nombre: str = Field(..., description="Nombre del departamento")


class ProvinciaOutput(BaseSchema):
    """Provincia del distrito."""
    id: uuid.UUID = Field(..., description="ID de la provincia")
    nombre: str = Field(..., description="Nombre de la provincia")


class DistritoOutput(BaseSchema):
    """Distrito del proyecto (con provincia y departamento anidados)."""
    id: uuid.UUID = Field(..., description="ID del distrito")
    nombre: str = Field(..., description="Nombre del distrito")
    ubigeo: Optional[str] = Field(None, description="Código ubigeo")
    provincia: Optional[ProvinciaOutput] = Field(None, description="Provincia del distrito")
    departamento: Optional[DepartamentoOutput] = Field(None, description="Departamento del distrito")


class ProyectoOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID del proyecto")
    nombre_propietario: str = Field(..., description="Nombre del propietario")
    direccion: str = Field(..., description="Dirección del propietario")
    urbanizacion: Optional[str] = Field(None, description="Urbanización o habilitación urbana del proyecto")
    distrito: Optional[DistritoOutput] = Field(None, description="Distrito del proyecto")
    entidad: EntidadInlineSchema = Field(..., description="Entidad propietaria")

# --- Contacto (In/Out) ---
class ContactoInlineSchema(BaseSchema):
    """Contacto principal de la liquidación — se crea inline como el proyecto."""
    nombres: str = Field(..., description="Nombres del contacto")
    apellidos: Optional[str] = Field(None, description="Apellidos del contacto")
    dni: Optional[str] = Field(None, description="DNI del contacto")
    cargo: Optional[str] = Field(None, description="Cargo del contacto")
    telefono: Optional[str] = Field(None, description="Teléfono del contacto")
    celular: Optional[str] = Field(None, description="Celular del contacto")
    email: Optional[str] = Field(None, description="Email del contacto")

class ContactoOutput(BaseSchema):
    """Contacto principal anidado en la respuesta."""
    id: uuid.UUID = Field(..., description="ID del contacto")
    nombres: Optional[str] = Field(None, description="Nombres del contacto")
    apellidos: Optional[str] = Field(None, description="Apellidos del contacto")
    dni: Optional[str] = Field(None, description="DNI del contacto")
    cargo: Optional[str] = Field(None, description="Cargo del contacto")
    telefono: Optional[str] = Field(None, description="Teléfono del contacto")
    celular: Optional[str] = Field(None, description="Celular del contacto")
    email: Optional[str] = Field(None, description="Email del contacto")


# --- Variables Financieras ---
class VariablesFinancierasNulasOut(BaseSchema):
    igv: Optional[dict] = Field(None, description="IGV nulo")
    uit: Optional[dict] = Field(None, description="UIT nulo")

class VariablesFinancierasBasicasOut(BaseSchema):
    igv: dict = Field(..., description="Objeto con valor y metadata del IGV vigente aplicado")
    uit: dict = Field(..., description="Objeto con valor y metadata de la UIT vigente aplicada")

# --- Mixins para composición de schemas ---

class LiquidacionRelacionadaMixin(BaseSchema):
    """
    Mixin base para inputs de /relacionada y /nueva-revision.

    Provee el campo `liquidacion_previa_id` que vincula la nueva liquidación
    a una liquidación previa existente en el mismo grupo de relación.

    Colocado aquí siguiendo el contrato SCHEMA_DRY_INTENTION de composición
    sobre herencia — este mixin se combina con los schemas de entrada
    (general + específica) para formar los payloads de endpoints relacionados.
    """
    liquidacion_previa_id: uuid.UUID = Field(
        ...,
        description="ID de la liquidación previa a la cual esta liquidación está relacionada",
    )


# --- Liquidacion General (Cabecera base) ---
class LiquidacionGeneralRevisionIn(BaseSchema):
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    retencion: Optional[bool] = Field(False, description="Indica si la liquidación tiene retención")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional)")
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")


class EntidadUpdateSchema(BaseSchema):
    """
    Partial update schema for nested Entidad inside Proyecto update.
    Only used within LiquidacionGeneralUpdateIn.proyecto.

    Rules:
    - tipo_documento + numero_documento: if numero_documento changes, triggers
      find-or-create Entidad and FK reassignment on Proyecto.
    - razon_social: updates Proyecto.entidad_razon_social snapshot only.
    - NEVER mutates an existing Entidad row.
    """
    tipo_documento: Optional[str] = Field(None, description="Tipo de documento (RUC/DNI)")
    numero_documento: Optional[str] = Field(None, description="Número de documento")
    razon_social: Optional[str] = Field(None, description="Razón social (actualiza snapshot en Proyecto)")


class ProyectoUpdateSchema(BaseSchema):
    """
    Partial update schema for Proyecto during liquidacion PATCH.
    All fields are optional — only provided fields are updated.

    Editable fields: nombre_propietario, direccion, distrito_id,
    urbanizacion, entidad (nested EntidadUpdateSchema).

    Excluded (not editable via PATCH):
    - entidad FK directly (use nested entidad update instead)
    - municipalidad_id (belongs to LiquidacionGeneral, not Proyecto)
    """
    nombre_propietario: Optional[str] = Field(None, description="Nombre del propietario")
    direccion: Optional[str] = Field(None, description="Dirección del proyecto")
    urbanizacion: Optional[str] = Field(None, description="Urbanización o habilitación urbana")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito")
    entidad: Optional[EntidadUpdateSchema] = Field(None, description="Entidad propietaria (parcial)")


class LiquidacionEliminarIn(BaseSchema):
    """Payload for PATCH /liquidaciones/generales/{id}/eliminar — marks a liquidacion as eliminated/anulled."""
    motivo: Optional[str] = Field(
        None,
        max_length=500,
        description="Motivo de la eliminación/anulación (auditable).",
    )


class LiquidacionGeneralUpdateIn(BaseSchema):
    """
    Schema for PATCH updates to general liquidacion fields.

    Only editable while estado == PENDIENTE.
    General fields: expediente, observacion, retencion, denominacion_de_proyecto, contacto.

    Conditionally editable (revision rule):
    - municipalidad_id: editable only when numero_revision == 1
    - proyecto: editable fields only when numero_revision == 1

    Excludes: estado, tipo_liquidacion, numero_revision, sub_total, total, igv, uit,
    fecha_registro (those require explicit state transitions or recalculation).
    """
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    retencion: Optional[bool] = Field(None, description="Indica si la liquidación tiene retención")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional)")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (opcional)")

    # Conditionally editable — revision rule applies (see orchestrator)
    municipalidad_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de municipalidad (solo editable si revision==1)",
    )
    proyecto: Optional[ProyectoUpdateSchema] = Field(
        None,
        description="Datos del proyecto (parcial, solo editable si revision==1)",
    )

class UsuarioCreadorOutput(BaseSchema):
    """Usuario creador completo (no solo id)."""
    id: uuid.UUID = Field(..., description="ID del usuario creador")
    nombres: Optional[str] = Field(None, description="Nombres del usuario")
    apellidos: Optional[str] = Field(None, description="Apellidos del usuario")
    email: Optional[str] = Field(None, description="Email del usuario")
    dni: Optional[str] = Field(None, description="DNI del usuario")
    username: Optional[str] = Field(None, description="Username del usuario")


class MunicipalidadOutput(BaseSchema):
    """Municipalidad en la respuesta de liquidación."""
    id: uuid.UUID = Field(..., description="ID de la municipalidad")
    codigo: str = Field(..., description="Código de la municipalidad")
    nombre: str = Field(..., description="Nombre de la municipalidad")


class IgvOutput(BaseSchema):
    """IGV aplicado en la liquidación."""
    id: uuid.UUID = Field(..., description="ID del IGV")
    valor: float = Field(..., description="Tasa IGV (0.18 = 18%)")
    periodo_inicio: Optional[str] = Field(None, description="Inicio de vigencia")


class UitOutput(BaseSchema):
    """UIT aplicada en la liquidación."""
    id: uuid.UUID = Field(..., description="ID de la UIT")
    valor: float = Field(..., description="Valor UIT en soles")
    periodo_inicio: Optional[str] = Field(None, description="Inicio de vigencia")


class TipoLiquidacionOutput(BaseSchema):
    """Tipo de liquidacion en la respuesta — solo codigo y nombre, sin id."""
    codigo: str = Field(..., description="Código del tipo de liquidación")
    nombre: str = Field(..., description="Nombre del tipo de liquidación")


class LiquidacionGeneralOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID de la liquidación general")
    estado: Optional[str] = Field(None, description="Estado de la liquidación: PENDIENTE (editable) o PAGADA (bloqueada)")
    municipalidad: MunicipalidadOutput = Field(..., description="Municipalidad de la liquidación")
    usuario_creador: Optional[UsuarioCreadorOutput] = Field(None, description="Usuario creador")
    fecha_registro: str = Field(..., description="Fecha de registro")
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    numero_revision: int = Field(..., description="Número de revisión")
    sub_total: float = Field(..., description="Subtotal")
    total: float = Field(..., description="Total")
    retencion: bool = Field(False, description="Indica si la liquidación tiene retención")
    legacy: bool = Field(False, description="Indica si la liquidación fue migrada del sistema legacy")
    codigo_cta: Optional[str] = Field(None, description="Código de cuenta associated con el tipo de liquidación (output only)")
    igv: Optional[IgvOutput] = Field(None, description="IGV aplicado")
    uit: Optional[UitOutput] = Field(None, description="UIT aplicada")
    proyecto: ProyectoOutput = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoOutput] = Field(None, description="Contacto principal")
    tipo_liquidacion: Optional[TipoLiquidacionOutput] = Field(None, description="Tipo de liquidación (codigo y nombre)")
    delegados: list[LiquidacionDelegadoEnGeneralOut] = Field(default_factory=list, description="Delegados asociados a la liquidación (estructura datos + delegado)")
    comprobantes: list[LiquidacionComprobanteOutput] = Field(default_factory=list, description="Todos los comprobantes de la liquidación (el activo tiene activo=True)")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto a nivel de liquidación")
    eliminado: bool = Field(False, description="Indica si la liquidación ha sido eliminada/anulada")
    fecha_eliminacion: Optional[str] = Field(None, description="Fecha y hora de eliminación/anulación")
    motivo_eliminacion: Optional[str] = Field(None, max_length=500, description="Motivo auditable de la eliminación/anulación")
    modo_calculo: str = Field("TARIFA", description="Modo de cálculo: TARIFA (normal por tarifa) o MANUAL (valores ingresados directamente)")


# Rebuild forward refs now that LiquidacionDelegadoEnGeneralOut has its delegated forward ref resolved
LiquidacionGeneralOutput.model_rebuild()
