"""
Legacy input schemas for Edificaciones (PorcentajeObra) — 100% additive, no existing schema modified.

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
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
)


class LiquidacionEdificacionesLegacyIn(BaseSchema):
    """
    Legacy input for Edificaciones with historical fecha_registro (supports any numero_revision).

    Mirrors LiquidacionEdificacionesInput structure but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)
    """
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
    numero: Optional[int] = Field(None, description="Número secuencial de la liquidación específica (legacy)")
    tipo_tramite: Optional[str] = Field(None, description="Tipo de trámite de edificación (TipoTramiteEdificaciones)")
