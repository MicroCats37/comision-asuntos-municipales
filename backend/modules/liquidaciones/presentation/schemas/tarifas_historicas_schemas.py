"""
Schemas for historical tariff and derecho endpoints.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from core.types import BaseSchema
from ninja import Field
from core.pagination import PaginatedData


# ── Query Params ──────────────────────────────────────────────────────────────

class TarifasHistoricasQueryParams(BaseSchema):
    """Query parameters for GET /liquidaciones/{tipo}/tarifas/historicas."""
    fecha_desde: Optional[date] = Field(default=None, description="Start date for the historical range; omit to get current vigentes")
    fecha_hasta: Optional[date] = Field(default=None, description="End date for the historical range; omit to get current vigentes")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")


class DerechosHistoricosQueryParams(BaseSchema):
    """Query parameters for GET /liquidaciones/derechos/historicos."""
    tipo: str = Field(..., description="Tipo de derecho: PORCENTAJE or METRO_CUADRADO")
    fecha_desde: Optional[date] = Field(default=None, description="Start date for the historical range; omit to get current vigentes")
    fecha_hasta: Optional[date] = Field(default=None, description="End date for the historical range; omit to get current vigentes")


# ── Tarifa Percentage Obra Detail ──────────────────────────────────────────────

class TarifaPorcentajeObraDetalleSchema(BaseSchema):
    """A single TarifaPorcentajeObra detail record."""
    id: UUID
    especialidad_id: UUID
    especialidad_nombre: str
    porcentaje_liquidacion: float


# ── Tarifa M2 Detail ────────────────────────────────────────────────────────────

class TarifaM2DetalleSchema(BaseSchema):
    """TarifaPorMetroCuadrado detail record."""
    id: UUID
    costo_por_m2: float


# ── Tarifa Visitas Detail ──────────────────────────────────────────────────────

class TarifaVisitasDetalleSchema(BaseSchema):
    """A single TarifaPorCategoriaVisitas detail record."""
    id: UUID
    categoria: str
    porcentaje_uit: float


# ── Tarifa Historica Periodo ───────────────────────────────────────────────────

class TarifaHistoricaPeriodoSchema(BaseSchema):
    """A single historical tariff period with its associated detail records."""
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
    """Response wrapper for historical tariffs."""
    periodos: List[TarifaHistoricaPeriodoSchema]


# ── Derecho Historico ──────────────────────────────────────────────────────────

class DerechoHistoricoSchema(BaseSchema):
    """A single historical derecho record."""
    id: UUID
    derecho_minimo: Optional[float] = None
    derecho_maximo: Optional[float] = None
    porcentaje_minimo_uit: Optional[float] = None
    periodo_inicio: date
    periodo_fin: Optional[date] = None


class DerechosHistoricosResponseSchema(BaseSchema):
    """Response wrapper for historical derechos."""
    derechos: List[DerechoHistoricoSchema]