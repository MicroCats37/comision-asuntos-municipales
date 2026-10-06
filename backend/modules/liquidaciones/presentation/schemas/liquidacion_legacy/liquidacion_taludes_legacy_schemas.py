"""
Legacy input schemas for Taludes (PorcentajeObra) — 100% additive, no existing schema modified.

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
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosIn,
    LiquidacionPorcentajeObraTarifaIn,
)


class CotizacionLegacyIn(BaseSchema):
    """
    Optional legacy totals bypass — when present, bypasses Steps 1-5 of
    calcular_cotizacion_po (valor declarado, mínimo UIT, topes) and uses
    the provided sub_total and total directly.
    """
    sub_total: Decimal
    total: Decimal


class LiquidacionTaludesLegacyIn(BaseSchema):
    """
    Legacy input for Taludes with historical fecha_registro (supports any numero_revision).

    Mirrors LiquidacionTaludesInput structure but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)
    """
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn
    cotizacion_legacy: Optional[CotizacionLegacyIn] = Field(
        None,
        description="Legacy totals bypass — uses Excel sub_total/total directly, skipping Steps 1-5",
    )
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
