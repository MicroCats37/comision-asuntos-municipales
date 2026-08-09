"""
Esquemas para Mecánica de Suelos — Solo el payload final de primera-revisión.

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
# POST /primera-revision — Schema específico de Mecánica de Suelos
# =============================================================================
class LiquidacionMecanicaSuelosInput(BaseSchema):
    """Payload de entrada: Cabecera Genérica + cálculo M2."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn


class LiquidacionMecanicaSuelosOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo M2."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput
    liquidacion_tipo: LiquidacionPorMetroCuadradoDatosOut
