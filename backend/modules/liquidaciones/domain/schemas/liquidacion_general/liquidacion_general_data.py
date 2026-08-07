from pydantic import BaseModel
from typing import Optional


class EntidadData(BaseModel):
    tipo_documento: str
    numero_documento: str


class ProyectoData(BaseModel):
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito_id: str
    entidad_razon_social: str
    entidad: EntidadData


class LiquidacionGeneralData(BaseModel):
    municipalidad_id: str
    expediente: str
    observacion: Optional[str] = None
    proyecto: ProyectoData
