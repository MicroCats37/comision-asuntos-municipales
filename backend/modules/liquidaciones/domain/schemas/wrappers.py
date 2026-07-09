"""
Wrapper Results — combinan resultado con datos de cálculo para presenters.

El cálculo no vive en LiquidacionXxxResult base para mantener
compatibilidad con el patrón existente de presenters que reciben
el cálculo como parámetro separado.
"""

from __future__ import annotations

from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.liquidaciones.domain.schemas.habilitacion_urbana import (
        LiquidacionHabilitacionUrbanaResult,
    )
    from modules.liquidaciones.domain.schemas.mecanica_suelos import (
        LiquidacionMecanicaSuelosResult,
    )
    from modules.liquidaciones.domain.schemas.impacto_vial import (
        LiquidacionImpactoVialResult,
    )
    from modules.liquidaciones.domain.schemas.taludes import (
        LiquidacionTaludesResult,
    )
    from modules.liquidaciones.domain.schemas.inspeccion_obra import (
        LiquidacionInspeccionObraResult,
    )
    from modules.liquidaciones.domain.schemas.shared import (
        LiquidacionM2CalculoData,
        LiquidacionVisitasCalculoData,
    )


# Alias for backwards compatibility with M2-based liquidations
# Each type maps to the same wrapper structure
LiquidacionM2Result = "LiquidacionHabilitacionUrbanaResult"


class LiquidacionM2ResultConCalculo(BaseModel):
    """
    Wrapper que combina resultado M2 con sus datos de cálculo M2.

    Evita tener que pasar el cálculo como argumento separado al presenter.
    """

    result: "LiquidacionHabilitacionUrbanaResult"
    calculo_m2: "LiquidacionM2CalculoData"


# Alias para uso directo en import
# These are all the same structure but imported by different names for clarity
LiquidacionHabilitacionUrbanaResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionMecanicaSuelosResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionImpactoVialResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionTaludesResultConCalculo = LiquidacionM2ResultConCalculo


class LiquidacionInspeccionObraResultConCalculo(BaseModel):
    """
    Wrapper que combina LiquidacionInspeccionObraResult con sus datos de cálculo visitas.
    """

    result: "LiquidacionInspeccionObraResult"
    calculo_visitas: "LiquidacionVisitasCalculoData"
