from pydantic import BaseModel
from typing import Optional


class EntidadResult(BaseModel):
    razon_social: str
    tipo_documento: str
    numero_documento: str


class ProyectoResult(BaseModel):
    id: str
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito_id: str  # Required by presenter
    entidad: Optional[EntidadResult] = None


class UsuarioCreadorResult(BaseModel):
    id: str


class ContactoResult(BaseModel):
    id: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None


class LiquidacionGeneralResult(BaseModel):
    id: str
    municipalidad_id: str
    usuario_creador: UsuarioCreadorResult
    fecha_registro: str  # NEW
    expediente: str
    observacion: Optional[str] = None
    numero_revision: int
    sub_total: float
    total: float
    igv_id: Optional[str] = None  # NEW
    uit_id: Optional[str] = None  # NEW
    proyecto: ProyectoResult
    contacto: Optional[ContactoResult] = None
