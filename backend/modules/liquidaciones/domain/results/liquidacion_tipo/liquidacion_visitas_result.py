from pydantic import BaseModel


class LiquidacionVisitasResult(BaseModel):
    id: str
    cantidad_visitas: int
    porcentaje_uit: float
    categoria: str
    tarifa_aplicada_id: str
