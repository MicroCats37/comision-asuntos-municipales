"""
Legacy input schemas for Habilitación Urbana (PorMetroCuadrado) — 100% additive, no existing schema modified.

Each legacy schema mirrors the existing input but with:
- Its own `liquidacion_general` inline (NOT reusing LiquidacionGeneralRevisionIn) + fecha_registro
- `numero_revision` as a top-level field with default 1
"""
from typing import Optional

from core.types import BaseSchema
from ninja import Field
from modules.liquidaciones.presentation.schemas.liquidacion_legacy._shared import (
    LiquidacionGeneralLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionPorMetroCuadradoIn,
    LiquidacionPorMetroCuadradoDatosIn,
    LiquidacionPorMetroCuadradoTarifaIn,
)


class LiquidacionHabilitacionUrbanaLegacyIn(BaseSchema):
    """
    Legacy input for Habilitación Urbana with historical fecha_registro (supports any numero_revision).

    Mirrors LiquidacionHabilitacionUrbanaInput structure but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)
    """
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
