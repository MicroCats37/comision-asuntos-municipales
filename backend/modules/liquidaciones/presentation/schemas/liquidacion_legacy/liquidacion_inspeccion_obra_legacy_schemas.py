"""
Legacy input schemas for Inspección de Obra (Visitas) — 100% additive, no existing schema modified.

Unlike the other 5 tipos, Inspección de Obra does not have a standalone primera-revision
input schema (its existing flow inherits from a previous liquidacion via liquidacion_previa_id).

The legacy schema for IO follows the same structural pattern as the other legacy schemas:
- Its own `liquidacion_general` inline with fecha_registro (mirrors LiquidacionGeneralRevisionIn fields)
- `numero_revision` as a top-level field with default 1
- `liquidacion_especifica` mirrors the existing IO-specific structure (datos + tarifa + inspector_id)

NOTE: IO legacy endpoint still requires liquidacion_previa_id because IO inherently
inherits proyecto/municipalidad/entidad from a prior liquidacion (Edificación or HU).
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from core.types import BaseSchema
from ninja import Field
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    EntidadInlineSchema,
    ProyectoCotizarSchema,
    ContactoInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraNuevaRevisionDatosIn,
    LiquidacionInspeccionObraNuevaRevisionTarifaIn,
    LiquidacionInspeccionObraNuevaRevisionEspecificaIn,
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


class LiquidacionInspeccionObraLegacyIn(BaseSchema):
    """
    Legacy input for Inspección de Obra primera-revision with historical fecha_registro.

    Mirrors the structure of LiquidacionInspeccionObraNuevaRevisionInput but:
    - Uses its own LiquidacionGeneralLegacyIn (inline, NOT reused from existing)
    - Adds numero_revision at top level (default 1)

    NOTE: IO inherits proyecto/municipalidad/entidad from a previous liquidacion,
    so liquidacion_previa_id is still required.
    """
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (Edificación o Habilitación Urbana)")
    liquidacion_general: LiquidacionGeneralLegacyIn
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn
    numero_revision: Optional[int] = Field(1, description="Número de revisión (default 1)")
