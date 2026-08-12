"""
Result de primera revisión de Edificaciones.
"""
from pydantic import BaseModel
from typing import List, Optional
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    LiquidacionPreviaResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import LiquidacionPorcentajeObraResult


class LiquidacionEspecificaEdificacionesResult(BaseModel):
    """Identidad: id + numero (AutoNumeroModel)."""
    id: str
    numero: int


class EdificacionesPrimeraRevisionResult(BaseModel):
    """Wrapper final: General + Específica + Tipo + revisiones_previas."""
    liquidacion_general: LiquidacionGeneralResult
    liquidacion_especifica: LiquidacionEspecificaEdificacionesResult
    liquidacion_tipo: LiquidacionPorcentajeObraResult
    revisiones_previas: List[LiquidacionPreviaResult] = []
