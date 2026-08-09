"""
DTO de dominio para creación de primera revisión de Impacto Vial.
Wrapper que combina LiquidacionGeneral + PorcentajeObra data.
"""
from pydantic import BaseModel
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import LiquidacionGeneralData
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import LiquidacionPorcentajeObraData


class ImpactoVialPrimeraRevisionData(BaseModel):
    """
    Wrapper Final para Impacto Vial (Primera Revisión).

    Importa limpiamente desde las capas General y Tipo.
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionPorcentajeObraData
