"""
General presentation schemas — Cabeceras y metadatos comunes a todo tipo de liquidación.
"""
from core.types import BaseSchema
from ninja import Field
from typing import Optional
import uuid

# --- Entidad & Proyecto (In/Out) ---
class EntidadInlineSchema(BaseSchema):
    tipo_documento: str = Field(..., description="Tipo de documento (RUC/DNI)")
    numero_documento: str = Field(..., description="Número de documento")
    razon_social: str = Field(..., description="Razón social o nombres")

class ProyectoCotizarSchema(BaseSchema):
    denominacion: str = Field(..., description="Denominación del proyecto")
    nombre_propietario: str = Field(..., description="Nombre del propietario")
    direccion: str = Field(..., description="Dirección del proyecto")
    distrito_id: uuid.UUID = Field(..., description="ID del distrito")
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
    denominacion: str = Field(..., description="Denominación del proyecto")
    nombre_propietario: str = Field(..., description="Nombre del propietario")
    direccion: str = Field(..., description="Dirección del proyecto")
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


class LiquidacionPreviaOutput(BaseSchema):
    """Resumen de una liquidación previa del mismo proyecto."""
    id: uuid.UUID = Field(..., description="ID de la liquidación previa")
    numero_revision: int = Field(..., description="Número de revisión de la previa")
    expediente: Optional[str] = Field(None, description="Expediente de la previa")

# --- Variables Financieras ---
class VariablesFinancierasNulasOut(BaseSchema):
    igv: Optional[dict] = Field(None, description="IGV nulo")
    uit: Optional[dict] = Field(None, description="UIT nulo")

class VariablesFinancierasBasicasOut(BaseSchema):
    igv: dict = Field(..., description="Objeto con valor y metadata del IGV vigente aplicado")
    uit: dict = Field(..., description="Objeto con valor y metadata de la UIT vigente aplicada")

# --- Liquidacion General (Cabecera base) ---
class LiquidacionGeneralRevisionIn(BaseSchema):
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: str = Field(..., description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    retencion: Optional[bool] = Field(False, description="Indica si la liquidación tiene retención")
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")

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


class LiquidacionGeneralOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID de la liquidación general")
    municipalidad: MunicipalidadOutput = Field(..., description="Municipalidad de la liquidación")
    usuario_creador: UsuarioCreadorOutput = Field(..., description="Usuario creador")
    fecha_registro: str = Field(..., description="Fecha de registro")
    expediente: str = Field(..., description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    numero_revision: int = Field(..., description="Número de revisión")
    sub_total: float = Field(..., description="Subtotal")
    total: float = Field(..., description="Total")
    retencion: bool = Field(False, description="Indica si la liquidación tiene retención")
    igv: Optional[IgvOutput] = Field(None, description="IGV aplicado")
    uit: Optional[UitOutput] = Field(None, description="UIT aplicada")
    proyecto: ProyectoOutput = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoOutput] = Field(None, description="Contacto principal")
    revisiones_previas: list[LiquidacionPreviaOutput] = Field(default_factory=list, description="Liquidaciones previas del mismo proyecto")
