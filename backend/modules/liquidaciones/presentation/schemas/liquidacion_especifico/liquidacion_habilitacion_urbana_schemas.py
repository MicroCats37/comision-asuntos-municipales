"""
Especifico Habilitación Urbana schemas — Solo el payload final de primera-revisión.

Todo lo de cotizar y tarifas vigentes vive en tipo/ porque es cálculo M2 reutilizable.
"""
from core.types import BaseSchema
import uuid

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
    LiquidacionGeneralOutput,
    LiquidacionRelacionadaMixin,
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


# =============================================================================
# POST /relacionada — Crea HU con numero_revision=1 relacionada a previa
# =============================================================================
class LiquidacionHabilitacionUrbanaRelacionadaInput(LiquidacionRelacionadaMixin):
    """
    Input para /relacionada — crea una nueva liquidacion HU con numero_revision=1
    vinculada a una liquidacion previa existente.

    Usa la misma estructura que primera-revision (full input) más el
    liquidacion_previa_id para establecer la relación de grupo.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn


# =============================================================================
# POST /nueva-revision — Crea HU con siguiente revisión impar (1→3→5)
# =============================================================================
class LiquidacionHabilitacionUrbanaNuevaRevisionInput(LiquidacionRelacionadaMixin):
    """
    Input para /nueva-revision — crea una nueva revisión HU (1→3, 3→5)
    basada en una liquidación previa existente.

    Los campos M2 (area_solicitada, tarifa) se proporcionan en el input.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn
