from pydantic import BaseModel
from typing import Optional
import uuid
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionCategoriaVisitasData,
)


class InspeccionObraNuevaRevisionData(BaseModel):
    """
    Wrapper para Inspección de Obra primera-revision desde liquidación previa.
    inspector_id es opcional — se valida contra inspector_operacion si ambos presentes.
    El inspector real se deriva de inspector_operacion.inspector en el flujo.
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionCategoriaVisitasData
    inspector_id: Optional[uuid.UUID] = None
