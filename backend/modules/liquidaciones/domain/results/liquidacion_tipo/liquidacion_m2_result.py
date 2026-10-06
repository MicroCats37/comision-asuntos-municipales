from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class LiquidacionM2Result(BaseModel):
    id: str
    area_m2: Decimal
    costo_por_m2: Optional[Decimal] = None  # null en modo MANUAL
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    derecho_aplicado_id: Optional[str] = None  # null en modo MANUAL
    tarifa_aplicada_id: Optional[str] = None  # null en modo MANUAL
