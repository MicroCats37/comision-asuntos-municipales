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

class ProyectoOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID del proyecto")
    denominacion: str = Field(..., description="Denominación del proyecto")
    nombre_propietario: str = Field(..., description="Nombre del propietario")
    direccion: str = Field(..., description="Dirección del proyecto")
    distrito_id: uuid.UUID = Field(..., description="ID del distrito")
    entidad: EntidadInlineSchema = Field(..., description="Entidad propietaria")

# --- Variables Financieras ---
class VariablesFinancierasNulasOut(BaseSchema):
    igv: Optional[dict] = Field(None, description="IGV nulo")
    uit: Optional[dict] = Field(None, description="UIT nulo")

# --- Liquidacion General (Cabecera base) ---
class LiquidacionGeneralRevisionIn(BaseSchema):
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: str = Field(..., description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")

class UsuarioCreadorOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID del usuario creador")

class LiquidacionGeneralOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID de la liquidación general")
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    usuario_creador: UsuarioCreadorOutput = Field(..., description="Usuario creador")
    fecha_registro: str = Field(..., description="Fecha de registro")
    expediente: str = Field(..., description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    numero_revision: int = Field(..., description="Número de revisión")
    sub_total: float = Field(..., description="Subtotal")
    total: float = Field(..., description="Total")
    igv_id: Optional[uuid.UUID] = Field(None, description="ID del IGV")
    uit_id: Optional[uuid.UUID] = Field(None, description="ID del UIT")
    derecho_id: Optional[uuid.UUID] = Field(None, description="ID del derecho aplicado")
    proyecto: ProyectoOutput = Field(..., description="Datos del proyecto")
