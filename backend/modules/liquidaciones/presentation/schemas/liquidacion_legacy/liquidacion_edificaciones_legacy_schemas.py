"""
Legacy input schemas for Edificaciones (PorcentajeObra) — 100% additive, no existing schema modified.

Each legacy schema mirrors the existing input but with:
- Its own `liquidacion_general` inline (NOT reusing LiquidacionGeneralRevisionIn) + fecha_registro
- `numero_revision` as a top-level field with default 1
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List
from core.types import BaseSchema
from ninja import Field
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    EntidadInlineSchema,
    ProyectoCotizarSchema,
    ContactoInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosIn,
    LiquidacionPorcentajeObraTarifaIn,
)


class LiquidacionGeneralLegacyIn(BaseSchema):
    """Inline liquidacion_general — mirrors LiquidacionGeneralRevisionIn fields + fecha_registro."""
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: str = Field(..., description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    retencion: Optional[bool] = Field(False, description="Indica si la liquidación tiene retención")
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")
    fecha_registro: Optional[date] = Field(None, description="Fecha de registro histórica (para tarifas legacy)")


class LiquidacionEdificacionesLegacyIn(BaseSchema):
    """
    Legacy input for Edificaciones primera-revision with historical fecha_registro.

    Mirrors LiquidacionEdificacionesInput structure but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)
    """
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
