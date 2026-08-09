from pydantic import BaseModel


class DatosVisitas(BaseModel):
    cantidad_visitas: int
    categoria: str


class TarifaVisitas(BaseModel):
    tarifa_visitas_id: str


class LiquidacionCategoriaVisitasData(BaseModel):
    datos: DatosVisitas
    tarifa: TarifaVisitas
