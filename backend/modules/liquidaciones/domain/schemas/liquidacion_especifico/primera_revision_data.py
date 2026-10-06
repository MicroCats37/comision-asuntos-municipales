"""
DTO de dominio para creación de primera revisión (motor PorcentajeObra).
Wrapper genérico que combina LiquidacionGeneral + PorcentajeObra data.
"""
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import LiquidacionGeneralData
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import LiquidacionPorcentajeObraData
from core.types import BaseSchema


class LiquidacionEspecificaPrimeraRevisionData(BaseSchema):
    """
    Wrapper genérico para Primera Revisión (motor PorcentajeObra).
    
    Combina LiquidacionGeneralData + LiquidacionPorcentajeObraData.
    Reemplaza a EdificacionesPrimeraRevisionData, TaludesPrimeraRevisionData,
    e ImpactoVialPrimeraRevisionData (que eran idénticos).
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionPorcentajeObraData
