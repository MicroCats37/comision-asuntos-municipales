from pydantic import BaseModel

from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)


class LiquidacionEspecificaHabilitacionUrbanaData(BaseModel):
    datos: DatosM2
    tarifa: TarifaM2


class HabilitacionUrbanaPrimeraRevisionData(BaseModel):
    """
    Wrapper Final para Habilitación Urbana (Primera Revisión).
    Importa limpiamente desde las capas General y Tipo.
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionEspecificaHabilitacionUrbanaData
