"""
Legacy input schemas for Mecánica de Suelos (PorMetroCuadrado) — 100% additive, no existing schema modified.

Each legacy schema mirrors the existing input but with:
- Its own `liquidacion_general` inline (NOT reusing LiquidacionGeneralRevisionIn) + fecha_registro
- `numero_revision` as a top-level field with default 1
"""
from decimal import Decimal
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


class CotizacionLegacyIn(BaseSchema):
    """
    Optional legacy totals bypass — when present, bypasses the M2 inline
    calculation and clamping, using the provided sub_total and total directly.
    """
    sub_total: Decimal
    total: Decimal


class LiquidacionMecanicaSuelosLegacyIn(BaseSchema):
    """
    Legacy input for Mecánica de Suelos with historical fecha_registro (supports any numero_revision).

    Mirrors LiquidacionMecanicaSuelosInput structure but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)
    """
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn
    cotizacion_legacy: Optional[CotizacionLegacyIn] = Field(
        None,
        description="Legacy totals bypass — uses Excel sub_total/total directly, bypassing M2 calculation and clamping",
    )
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
