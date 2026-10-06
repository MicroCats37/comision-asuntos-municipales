from core.types import BaseSchema
from typing import Optional


class EntidadData(BaseSchema):
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None


class ProyectoData(BaseSchema):
    nombre_propietario: str
    direccion: str
    distrito_id: str
    urbanizacion: Optional[str] = None
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
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    retencion: bool = False
    proyecto: ProyectoData
    contacto: Optional[ContactoData] = None
    denominacion_de_proyecto: Optional[str] = None
    descripcion_legacy: Optional[str] = None
