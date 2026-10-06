"""
Esquemas para endpoints de tarifas históricas y derechos.
"""
from datetime import date
from typing import List, Literal, Optional, Union
from uuid import UUID

from core.types import BaseSchema
from ninja import Field
from core.pagination import PaginatedData


# ── Query Params ──────────────────────────────────────────────────────────────

class TarifasHistoricasQueryParams(BaseSchema):
    """Parámetros de consulta para GET /liquidaciones/{tipo}/tarifas/historicas."""
    fecha_desde: Optional[date] = Field(default=None, description="Fecha de inicio del rango histórico; omitir para obtener vigentes actuales")
    fecha_hasta: Optional[date] = Field(default=None, description="Fecha de fin del rango histórico; omitir para obtener vigentes actuales")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")


class DerechosHistoricosQueryParams(BaseSchema):
    """Parámetros de consulta para GET /liquidaciones/derechos/historicos."""
    tipo: str = Field(..., description="Tipo de derecho: PORCENTAJE or METRO_CUADRADO")
    fecha_desde: Optional[date] = Field(default=None, description="Fecha de inicio del rango histórico; omitir para obtener vigentes actuales")
    fecha_hasta: Optional[date] = Field(default=None, description="Fecha de fin del rango histórico; omitir para obtener vigentes actuales")


# ── Tarifa Percentage Obra Detail ──────────────────────────────────────────────

class TarifaPorcentajeObraDetalleSchema(BaseSchema):
    """Un único registro de detalle de TarifaPorcentajeObra."""
    id: UUID
    especialidad_id: UUID
    especialidad_nombre: str
    porcentaje_liquidacion: float


# ── Tarifa M2 Detail ────────────────────────────────────────────────────────────

class TarifaM2DetalleSchema(BaseSchema):
    """Registro de detalle de TarifaPorMetroCuadrado."""
    id: UUID
    costo_por_m2: float


# ── Tarifa Visitas Detail ──────────────────────────────────────────────────────

class TarifaVisitasDetalleSchema(BaseSchema):
    """Un único registro de detalle de TarifaPorCategoriaVisitas."""
    id: UUID
    categoria: str
    porcentaje_uit: float


# ── Tarifa Historica Periodo ───────────────────────────────────────────────────

class TarifaHistoricaPeriodoSchema(BaseSchema):
    """Un único período de tarifa histórica con sus registros de detalle asociados."""
    id: UUID
    tipo_liquidacion: str
    periodo_inicio: date
    periodo_fin: Optional[date]
    # Percentage type details (for Edificaciones, IV, Taludes)
    tarifas_porcentaje: List[TarifaPorcentajeObraDetalleSchema] = Field(default_factory=list)
    # M2 type detail (for HU, MS) — only one per base
    tarifa_m2: Optional[TarifaM2DetalleSchema] = None
    # Visitas type details (for IO) — multiple per base
    tarifas_visitas: List[TarifaVisitasDetalleSchema] = Field(default_factory=list)


class TarifasHistoricasResponseSchema(BaseSchema):
    """Contenedor de respuesta para tarifas históricas."""
    periodos: List[TarifaHistoricaPeriodoSchema]


# ── General Endpoint Schemas (discriminated union) ────────────────────────────

class TarifaPorcentajeGeneralSchema(BaseSchema):
    """Detail for porcentaje-type tariff items (EDIFICACION, IMPACTO_VIAL, TALUDES)."""
    id: UUID
    especialidad: str  # especialidad_nombre from the domain
    porcentaje: float


class TarifaM2GeneralSchema(BaseSchema):
    """Detail for m2-type tariff items (HABILITACION_URBANA, MECANICA_SUELOS)."""
    id: UUID
    monto: float  # costo_por_m2 from the domain


class TarifaVisitasGeneralSchema(BaseSchema):
    """Detail for visitas-type tariff items (INSPECCION_OBRA)."""
    id: UUID
    categoria: str
    porcentaje_uit: float


class TarifaPorcentajeItemSchema(BaseSchema):
    """Discriminated item for porcentaje-type tariffs."""
    tipo_tarifa: Literal["porcentaje"]
    tipo_liquidacion: str
    periodo_inicio: date
    periodo_fin: Optional[date]
    tarifa_porcentaje: TarifaPorcentajeGeneralSchema


class TarifaM2ItemSchema(BaseSchema):
    """Discriminated item for m2-type tariffs."""
    tipo_tarifa: Literal["m2"]
    tipo_liquidacion: str
    periodo_inicio: date
    periodo_fin: Optional[date]
    tarifa_m2: TarifaM2GeneralSchema


class TarifaVisitasItemSchema(BaseSchema):
    """Discriminated item for visitas-type tariffs."""
    tipo_tarifa: Literal["visitas"]
    tipo_liquidacion: str
    periodo_inicio: date
    periodo_fin: Optional[date]
    tarifa_visitas: TarifaVisitasGeneralSchema


# Union type alias for general endpoint response items
TarifaGeneralItem = TarifaPorcentajeItemSchema | TarifaM2ItemSchema | TarifaVisitasItemSchema


class TarifasGeneralesQueryParams(BaseSchema):
    """Query params for GET /liquidaciones/tarifas (general endpoint)."""
    vigentes: bool = Field(default=False, description="If true, return vigentes at fecha_ref; if false, return all tariffs optionally filtered by date range")
    fecha_ref: Optional[date] = Field(default=None, description="Reference date for vigentes filter (default: today)")
    fecha_desde: Optional[date] = Field(default=None, description="Start of historical date range (for vigentes=false)")
    fecha_hasta: Optional[date] = Field(default=None, description="End of historical date range (for vigentes=false)")


# ── Derecho Historico ──────────────────────────────────────────────────────────

class DerechoHistoricoSchema(BaseSchema):
    """Un único registro de derecho histórico."""
    id: UUID
    derecho_minimo: Optional[float] = None
    derecho_maximo: Optional[float] = None
    porcentaje_minimo_uit: Optional[float] = None
    periodo_inicio: date
    periodo_fin: Optional[date] = None


class DerechosHistoricosResponseSchema(BaseSchema):
    """Contenedor de respuesta para derechos históricos."""
    derechos: List[DerechoHistoricoSchema]
