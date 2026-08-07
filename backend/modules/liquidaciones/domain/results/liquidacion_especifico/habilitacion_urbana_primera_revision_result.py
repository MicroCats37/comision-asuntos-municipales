from pydantic import BaseModel
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
    LiquidacionM2Result,
)


class LiquidacionEspecificaHabilitacionUrbanaResult(BaseModel):
    id: str
    numero: int


class HabilitacionUrbanaPrimeraRevisionResult(BaseModel):
    """
    Wrapper Final para Habilitación Urbana (Primera Revisión).
    Tipado estricto (cero dicts) importando de las capas base.
    """
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_tipo: LiquidacionM2Result
    liquidacion_especifica: LiquidacionEspecificaHabilitacionUrbanaResult
