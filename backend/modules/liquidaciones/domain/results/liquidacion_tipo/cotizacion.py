from pydantic import BaseModel
import uuid
from decimal import Decimal
from typing import Optional, List

class CotizacionM2Result(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización M2."""
    area_m2: float
    costo_por_m2: float
    tarifa_id: str
    derecho_id: str
    minimo: float
    maximo: Optional[float] = None
    monto_bruto: float
    subtotal: float
    total: float


class CotizacionVisitasResult(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización de Visitas."""
    cantidad_visitas: int
    categoria: str
    costo_por_visita: float
    tarifa_id: str
    monto_bruto: float
    subtotal: float
    total: float
    uit: dict
    igv: dict


class CotizacionPorcentajeObraDetalleResult(BaseModel):
    """Detalle de cotización porcentual (no persiste)."""
    tarifa_id: str
    porcentaje_aplicado: Decimal
    subtotal: Decimal
    igv: Decimal
    uit: Decimal
    total: Decimal


class CotizacionPorcentajeObraResult(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización PorcentajeObra."""
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: str
    detalles: List[CotizacionPorcentajeObraDetalleResult]
    total_subtotal: Decimal
    total: Decimal
