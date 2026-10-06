from pydantic import BaseModel
from typing import Optional


class DatosVisitas(BaseModel):
    cantidad_visitas: int
    categoria: Optional[str] = None  # nullable for CATEGORIA=0 legacy records


class TarifaVisitas(BaseModel):
    # Nullable: normal path requires valid tarifa_visitas_id;
    # legacy/manual path (cotizacion_legacy with no tariff) passes None.
    tarifa_visitas_id: Optional[str] = None


class LiquidacionCategoriaVisitasData(BaseModel):
    datos: DatosVisitas
    tarifa: TarifaVisitas
