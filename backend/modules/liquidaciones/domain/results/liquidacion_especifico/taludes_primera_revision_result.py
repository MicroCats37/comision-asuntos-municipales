"""
Result de primera revisión de Taludes.
"""
from pydantic import BaseModel
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import LiquidacionGeneralResult
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import LiquidacionPorcentajeObraResult


class LiquidacionEspecificaTaludesResult(BaseModel):
    """Identidad: id + numero (AutoNumeroModel)."""
    id: str
    numero: int


class TaludesPrimeraRevisionResult(BaseModel):
    """Wrapper final: General + Específica + Tipo."""
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_especifica: LiquidacionEspecificaTaludesResult
    liquidacion_tipo: LiquidacionPorcentajeObraResult
