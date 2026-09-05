from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class LiquidacionM2Result(BaseModel):
    id: str
    area_m2: Decimal
    costo_por_m2: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    derecho_aplicado_id: str
    tarifa_aplicada_id: str
