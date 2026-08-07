from pydantic import BaseModel
import uuid
from decimal import Decimal
from typing import Optional

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
