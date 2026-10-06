"""
PATCH input schemas for M2 types (Habilitacion Urbana, Mecanica Suelos).

Two input formats are supported:
1. Flat (legacy): `LiquidacionPatchM2In` — direct calculation fields only.
2. Wrapper (current): `LiquidacionPatchM2WrapperIn` — `liquidacion_general` + `liquidacion_tipo`
   matching the creation contract structure.

Used by PATCH /liquidaciones/{type}/{id} endpoints for recalculating
calculation inputs (area_solicitada, tarifa_m2_id) while keeping the
liquidacion in PENDIENTE state.
"""
import uuid
from decimal import Decimal
from typing import Optional

from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadUpdateSchema,
    ProyectoUpdateSchema,
)


class LiquidacionPatchM2In(BaseSchema):
    """
    PATCH input for M2 recalculation (flat/legacy format).

    All fields are optional — omitted fields preserve current stored values.

    Business rules:
    - area_solicitada: optional; if provided must be > 0.
    - tarifa_m2_id: optional; if provided must be vigente at fecha_registro.
    - Only editable when estado == PENDIENTE.
    """
    area_solicitada: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo area solicitada en m2 (opcional, preserva actual si se omite)",
    )
    tarifa_m2_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa M2 a aplicar (opcional, preserva actual si se omite)",
    )


# ── Wrapper schema (liquidacion_general + liquidacion_tipo) ──────────────────

class LiquidacionPatchM2GeneralIn(BaseSchema):
    """
    Partial update schema for general fields inside M2 PATCH wrapper.

    Exposes the same conditional-editing rules as LiquidacionGeneralUpdateIn
    (municipalidad_id and proyecto only editable at revision 1 with no previas).

    Fields are optional — omitted fields preserve current stored values.
    """
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    retencion: Optional[bool] = Field(None, description="Indica si la retención es obligatoria")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional)")
    contacto: Optional[ContactoInlineSchema] = Field(
        None,
        description="Contacto principal (opcional)",
    )
    municipalidad_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de municipalidad (solo editable si revision==1 y sin previas)",
    )
    proyecto: Optional[ProyectoUpdateSchema] = Field(
        None,
        description="Datos del proyecto (parcial, solo editable si revision==1 y sin previas)",
    )


class LiquidacionPatchM2DatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for M2 PATCH."""
    area_solicitada: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo area solicitada en m2 (opcional, preserva actual si se omite)",
    )


class LiquidacionPatchM2TarifaIn(BaseSchema):
    """Tarifa portion of liquidacion_tipo for M2 PATCH."""
    tarifa_m2_id: uuid.UUID = Field(..., description="ID de la tarifa M2 a aplicar")


class LiquidacionPatchM2TipoIn(BaseSchema):
    """
    liquidacion_tipo wrapper for M2 PATCH — mirrors creation structure.

    All fields optional — omitted fields preserve current stored values.
    """
    datos: Optional[LiquidacionPatchM2DatosIn] = Field(
        None,
        description="Datos del cálculo (area_solicitada)",
    )
    tarifa: Optional[LiquidacionPatchM2TarifaIn] = Field(
        None,
        description="Tarifa M2 a aplicar",
    )


class LiquidacionPatchM2WrapperIn(BaseSchema):
    """
    Wrapper PATCH input for M2 types (Habilitacion Urbana, Mecanica Suelos).

    Supports two input formats:
    1. Wrapper (current/recommended): liquidacion_general + liquidacion_tipo
    2. Flat (legacy/backward compat): area_solicitada + tarifa_m2_id directly

    Both wrappers are optional; only provided fields are updated.
    The state guard (PENDIENTE) applies to both general and tipo updates.
    PAGADA blocks the entire PATCH regardless of which wrapper is provided.

    When both wrapper and flat fields are provided, wrapper takes precedence.
    """
    # Wrapper format (recommended)
    liquidacion_general: Optional[LiquidacionPatchM2GeneralIn] = Field(
        None,
        description="Campos generales opcionales (expediente, proyecto, municipalidad, etc.)",
    )
    liquidacion_tipo: Optional[LiquidacionPatchM2TipoIn] = Field(
        None,
        description="Campos de cálculo tipo M2 opcionales (datos, tarifa) — estilo creación",
    )
    # Flat format (legacy/backward compat)
    area_solicitada: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo area solicitada en m2 (flat legacy format, opcional)",
    )
    tarifa_m2_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa M2 a aplicar (flat legacy format, opcional)",
    )
