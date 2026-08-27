from pydantic import BaseModel
from typing import Optional
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
    LiquidacionVisitasResult,
)


class LiquidacionEspecificaInspeccionObraResult(BaseModel):
    id: str
    numero: Optional[int] = None


class InspeccionObraPrimeraRevisionResult(BaseModel):
    """
    Wrapper Final para Inspección de Obra (Primera Revisión).
    Tipado estricto (cero dicts) importando de las capas base.
    """
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_tipo: LiquidacionVisitasResult
    liquidacion_especifica: LiquidacionEspecificaInspeccionObraResult
