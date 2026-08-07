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
    entidad: Optional[EntidadResult] = None


class UsuarioCreadorResult(BaseModel):
    id: str


class LiquidacionGeneralResult(BaseModel):
    id: str
    municipalidad_id: str
    usuario_creador: UsuarioCreadorResult
    expediente: str
    observacion: Optional[str] = None
    numero_revision: int
    sub_total: float
    total: float
    proyecto: ProyectoResult
