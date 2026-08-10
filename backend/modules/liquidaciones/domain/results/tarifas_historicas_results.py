"""
Domain results for historical tariff queries.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from uuid import UUID


@dataclass
class TarifaPorcentajeObraDetalleResult:
    """A single TarifaPorcentajeObra with its especialidad."""
    id: UUID
    especialidad_id: UUID
    especialidad_nombre: str
    porcentaje_liquidacion: float


@dataclass
class TarifaM2Result:
    """TarifaPorMetroCuadrado data."""
    id: UUID
    costo_por_m2: float


@dataclass
class TarifaVisitasResult:
    """TarifaPorCategoriaVisitas data."""
    id: UUID
    categoria: str
    porcentaje_uit: float


@dataclass
class TarifaHistoricaPeriodoResult:
    """A historical tariff period with its associated detail records."""
    id: UUID
    tipo_liquidacion: str
    periodo_inicio: date
    periodo_fin: Optional[date]
    # Percentage type details
    tarifas_porcentaje: List[TarifaPorcentajeObraDetalleResult]
    # M2 type detail (only one per base)
    tarifa_m2: Optional[TarifaM2Result]
    # Visitas type details (multiple per base)
    tarifas_visitas: List[TarifaVisitasResult]


@dataclass
class DerechoHistoricoResult:
    """A historical derecho record."""
    id: UUID
    derecho_minimo: Optional[float]
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: Optional[float]
    periodo_inicio: date
    periodo_fin: Optional[date]