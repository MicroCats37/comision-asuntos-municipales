"""
Result de primera revisión (motor PorcentajeObra).
DTOs internos — heredan de BaseModel (no BaseSchema).
"""
from pydantic import BaseModel
from typing import List, Optional
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    LiquidacionPreviaResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import LiquidacionPorcentajeObraResult


class LiquidacionEspecificaResult(BaseModel):
    """Identidad: id + numero (AutoNumeroModel)."""
    id: str
    numero: Optional[int] = None


class LiquidacionEspecificaPrimeraRevisionResult(BaseModel):
    """
    Wrapper final para Primera Revisión (motor PorcentajeObra).
    
    Combina LiquidacionGeneralResult + LiquidacionEspecificaResult + LiquidacionPorcentajeObraResult.
    Reemplaza a EdificacionesPrimeraRevisionResult, TaludesPrimeraRevisionResult,
    e ImpactoVialPrimeraRevisionResult (que tenían la misma estructura).
    
    Nota: revisiones_previas es opcional (presente en Edificaciones, absent en Taludes/ImpactoVial).
    """
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_especifica: LiquidacionEspecificaResult
    liquidacion_tipo: LiquidacionPorcentajeObraResult
    revisiones_previas: List[LiquidacionPreviaResult] = []
