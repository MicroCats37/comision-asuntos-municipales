from pydantic import BaseModel
from decimal import Decimal


class DatosM2(BaseModel):
    area_solicitada: Decimal


class TarifaM2(BaseModel):
    tarifa_m2_id: str
