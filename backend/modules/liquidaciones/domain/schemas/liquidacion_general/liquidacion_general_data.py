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


class ContactoData(BaseModel):
    """Contacto principal de la liquidación (se crea inline)."""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None


class LiquidacionGeneralData(BaseModel):
    municipalidad_id: str
    expediente: str
    observacion: Optional[str] = None
    proyecto: ProyectoData
    contacto: Optional[ContactoData] = None
