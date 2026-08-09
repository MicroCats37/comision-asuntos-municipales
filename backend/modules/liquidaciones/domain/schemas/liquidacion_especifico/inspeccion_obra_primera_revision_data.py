from pydantic import BaseModel
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionCategoriaVisitasData,
)


class InspeccionObraPrimeraRevisionData(BaseModel):
    """
    Wrapper Final para Inspección de Obra (Primera Revisión).
    Importa limpiamente desde las capas General y Tipo.
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionCategoriaVisitasData
