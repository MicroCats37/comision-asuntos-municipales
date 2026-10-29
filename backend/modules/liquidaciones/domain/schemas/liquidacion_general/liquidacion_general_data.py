from core.types import BaseSchema
from typing import Optional


class EntidadData(BaseSchema):
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None


class ProyectoData(BaseSchema):
    nombre_propietario: str
    direccion: str
    distrito_id: Optional[str] = None
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
    proyecto: ProyectoData
    contacto: Optional[ContactoData] = None
    denominacion_de_proyecto: Optional[str] = None
    descripcion_legacy: Optional[str] = None
    # Número de revisión elegido por el cliente (1, 3 o 5). Viaja hasta el flujo
    # para persistirse TAL CUAL en `LiquidacionGeneral` y en el miembro de relación,
    # dentro de la misma transacción. El backend nunca lo deriva ni lo recalcula.
    # Es opcional solo porque los caminos legacy/edge lo reciben por otro
    # parámetro explícito; en creación/relacionada/nueva revisión es obligatorio.
    numero_revision: Optional[int] = None
