from pydantic import BaseModel
from typing import Optional


class LiquidacionM2Result(BaseModel):
    id: str
    area_m2: float
    costo_por_m2: float
    derecho_minimo: float
    derecho_maximo: Optional[float] = None
    derecho_aplicado_id: str
    tarifa_aplicada_id: str
