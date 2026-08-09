"""
Domain results for Mecanica Suelos primera revision.
"""
from pydantic import BaseModel

from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
    LiquidacionM2Result,
)


class LiquidacionEspecificaMecanicaSuelosResult(BaseModel):
    id: str
    numero: int


class MecanicaSuelosPrimeraRevisionResult(BaseModel):
    """
    Wrapper Final para Mecánica de Suelos (Primera Revisión).
    Tipado estricto (cero dicts) importando de las capas base.
    """
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_tipo: LiquidacionM2Result
    liquidacion_especifica: LiquidacionEspecificaMecanicaSuelosResult
