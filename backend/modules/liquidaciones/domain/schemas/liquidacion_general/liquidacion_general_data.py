from core.types import BaseSchema
from typing import Optional


class EntidadData(BaseSchema):
    tipo_documento: str
    numero_documento: str


class ProyectoData(BaseSchema):
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito_id: str
    entidad_razon_social: str
    entidad: EntidadData


class ContactoData(BaseSchema):
    """Contacto principal de la liquidación (se crea inline)."""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None


class LiquidacionGeneralData(BaseSchema):
    municipalidad_id: str
    expediente: str
    observacion: Optional[str] = None
    retencion: bool = False
    proyecto: ProyectoData
    contacto: Optional[ContactoData] = None
