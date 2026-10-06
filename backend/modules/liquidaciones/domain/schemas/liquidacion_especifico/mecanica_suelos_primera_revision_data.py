"""
Domain DTOs for Mecanica Suelos primera revision.
"""
from pydantic import BaseModel

from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result


class LiquidacionEspecificaMecanicaSuelosData(BaseModel):
    datos: DatosM2
    tarifa: TarifaM2


class MecanicaSuelosPrimeraRevisionData(BaseModel):
    """
    Wrapper Final para Mecánica de Suelos (Primera Revisión).
    Importa limpiamente desde las capas General y Tipo.

    El campo `cotizacion` contiene el resultado PRE-CLAMPED del cálculo M2.
    El clamping se aplica en el Orchestrator (único lugar con esa responsabilidad).
    """
    liquidacion_general: LiquidacionGeneralData
    liquidacion_especifica: LiquidacionEspecificaMecanicaSuelosData
    cotizacion: CotizacionM2Result
