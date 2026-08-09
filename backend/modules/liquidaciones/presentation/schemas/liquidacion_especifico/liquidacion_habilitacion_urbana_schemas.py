"""
Especifico Habilitación Urbana schemas — Solo el payload final de primera-revisión.

Todo lo de cotizar y tarifas vigentes vive en tipo/ porque es cálculo M2 reutilizable.
"""
from core.types import BaseSchema
import uuid

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionPorMetroCuadradoIn,
    LiquidacionPorMetroCuadradoDatosOut,
    LiquidacionTipoOutput,
)


# =============================================================================
# POST /primera-revision — Único schema verdaderamente específico de HU
# =============================================================================
class LiquidacionHabilitacionUrbanaInput(BaseSchema):
    """Payload de entrada: Cabecera Genérica + cálculo M2."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn

class LiquidacionHabilitacionUrbanaOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo M2."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput
    liquidacion_tipo: LiquidacionPorMetroCuadradoDatosOut
