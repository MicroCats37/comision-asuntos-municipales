"""
Shared domain schemas stub.

This file exists to satisfy imports from domain/schemas/__init__.py.
"""
from pydantic import BaseModel
from typing import Optional
import uuid


class EntidadInlineData(BaseModel):
    id: uuid.UUID
    razon_social: Optional[str] = None
    tipo_documento: str
    numero_documento: str


class ProyectoInlineData(BaseModel):
    id: uuid.UUID
    denominacion: str
    entidad_razon_social: Optional[str] = None
    entidad_tipo_documento: Optional[str] = None
    entidad_numero_documento: Optional[str] = None
    nombre_propietario: str
    direccion: Optional[str] = None
    urbanizacion: Optional[str] = None


class VariablesFinancierasResult(BaseModel):
    igv_valor: float
    uit_valor: float


class TarifaM2CalculoData(BaseModel):
    costo_por_m2: float
    minimo: float
    maximo: Optional[float] = None


class LiquidacionM2CalculoData(BaseModel):
    area_m2: float
    costo_por_m2: float
    minimo: float
    maximo: Optional[float] = None


class TarifaVisitasCalculoData(BaseModel):
    costo_por_visita: float
    visitas_minimas: int


class LiquidacionVisitasCalculoData(BaseModel):
    cantidad_visitas: int
    costo_por_visita: float
    porcentaje_uit: float


class CotizacionM2RevisionData(BaseModel):
    pass


class CotizacionVisitasRevisionData(BaseModel):
    pass


class CotizacionM2QuoteData(BaseModel):
    pass


class CotizacionVisitasQuoteData(BaseModel):
    pass
