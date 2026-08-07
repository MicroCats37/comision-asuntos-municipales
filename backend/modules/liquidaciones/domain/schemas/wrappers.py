"""
Domain schemas wrappers that combine results with calculation data.

This file exists to satisfy imports from domain/schemas/__init__.py.
"""
from pydantic import BaseModel
from typing import Optional

from modules.liquidaciones.domain.schemas.habilitacion_urbana import (
    LiquidacionHabilitacionUrbanaResult,
)


class LiquidacionM2ResultConCalculo(BaseModel):
    """Wrapper for M2 liquidacion result with calculation data."""
    pass


class LiquidacionInspeccionObraResultConCalculo(BaseModel):
    """Wrapper for Inspeccion Obra result with calculation data."""
    pass


class LiquidacionHabilitacionUrbanaResultConCalculo(BaseModel):
    """Wrapper for HU result with calculation data."""
    result: LiquidacionHabilitacionUrbanaResult


class LiquidacionMecanicaSuelosResultConCalculo(BaseModel):
    """Wrapper for Mecanica Suelos result with calculation data."""
    pass


class LiquidacionImpactoVialResultConCalculo(BaseModel):
    """Wrapper for Impacto Vial result with calculation data."""
    pass


class LiquidacionTaludesResultConCalculo(BaseModel):
    """Wrapper for Taludes result with calculation data."""
    pass
