"""
Especifico Inspección de Obra schemas — Solo el payload final de primera-revisión.
"""
from core.types import BaseSchema

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasIn,
    LiquidacionPorCategoriaVisitasDatosOut,
)


# =============================================================================
# POST /primera-revision — Único schema verdaderamente específico de Inspeccion de Obra
# =============================================================================
class LiquidacionInspeccionObraInput(BaseSchema):
    """Payload de entrada: Cabecera Genérica + cálculo de Visitas."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorCategoriaVisitasIn


class LiquidacionInspeccionObraOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo de Visitas."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_tipo: LiquidacionTipoOutput
    liquidacion_especifica: LiquidacionPorCategoriaVisitasDatosOut
