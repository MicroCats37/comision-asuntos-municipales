"""
Esquemas para Mecánica de Suelos — Solo el payload final de primera-revisión.

Todo lo de cotizar y tarifas vigentes vive en tipo/ porque es cálculo M2 reutilizable.
"""
from core.types import BaseSchema
import uuid

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
    LiquidacionGeneralOutput,
    LiquidacionRelacionadaMixin,
    NumeroRevisionRequeridoMixin,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionPorMetroCuadradoIn,
    LiquidacionPorMetroCuadradoDatosOut,
    LiquidacionTipoOutput,
)


# =============================================================================
# POST /primera-revision — Schema específico de Mecánica de Suelos
# =============================================================================
class LiquidacionMecanicaSuelosInput(NumeroRevisionRequeridoMixin):
    """Payload de entrada: Cabecera Genérica + cálculo M2 + número de revisión."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn


class LiquidacionMecanicaSuelosOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo M2."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput
    liquidacion_tipo: LiquidacionPorMetroCuadradoDatosOut


# =============================================================================
# POST /relacionada — Crea MS relacionada a previa
# =============================================================================
class LiquidacionMecanicaSuelosRelacionadaInput(
    LiquidacionRelacionadaMixin,
    NumeroRevisionRequeridoMixin,
):
    """
    Input para /relacionada — crea una nueva liquidacion MS vinculada a una
    liquidacion previa existente, con el número de revisión elegido por el usuario.

    Usa la misma estructura que primera-revision (full input) más el
    liquidacion_previa_id para establecer la relación de grupo.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn


# =============================================================================
# POST /nueva-revision — Crea MS con nueva revisión (1→3→5)
# =============================================================================
class LiquidacionMecanicaSuelosNuevaRevisionInput(
    LiquidacionRelacionadaMixin,
    NumeroRevisionRequeridoMixin,
):
    """
    Input para /nueva-revision — crea una nueva revisión MS (1→3, 3→5)
    basada en una liquidación previa existente, con el número de revisión
    elegido por el usuario.

    Los campos M2 (area_solicitada, tarifa) se proporcionan frescos en el input.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn
