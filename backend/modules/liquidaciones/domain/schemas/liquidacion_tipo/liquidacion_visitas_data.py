from pydantic import BaseModel


class DatosVisitas(BaseModel):
    cantidad_visitas: int
    categoria: str


class TarifaVisitas(BaseModel):
    tarifa_visitas_id: str


class LiquidacionTipoVisitasData(BaseModel):
    datos: DatosVisitas
    tarifa: TarifaVisitas
