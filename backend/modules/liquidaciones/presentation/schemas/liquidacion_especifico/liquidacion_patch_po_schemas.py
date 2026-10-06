"""
PATCH input schemas for PorcentajeObra types (Edificaciones, Impacto Vial, Taludes).

Two input formats are supported:
1. Flat (legacy): `LiquidacionPatchPOIn` — direct calculation fields only.
2. Wrapper (current): `LiquidacionPatchPOWrapperIn` — `liquidacion_general` + `liquidacion_tipo`
   matching the creation contract structure.

Used by PATCH /liquidaciones/{type}/{id} endpoints for recalculating
calculation inputs (valor_declarado, tarifas) while keeping the
liquidacion in PENDIENTE state.
"""
import uuid
from decimal import Decimal
from typing import Optional, List

from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadUpdateSchema,
    ProyectoUpdateSchema,
)


class TarifaPatchIn(BaseSchema):
    """A single tariff + especialidad pair for PATCH recalculation of PO types."""
    tarifa_id: uuid.UUID = Field(..., description="ID of the TarifaPorcentajeObra to apply")
    especialidad_id: uuid.UUID = Field(..., description="ID of the especialidad")


class LiquidacionPatchPOIn(BaseSchema):
    """
    PATCH input for PorcentajeObra recalculation (flat/legacy format).

    All fields are optional — omitted fields preserve current stored values.

    Business rules:
    - valor_declarado: optional; if provided must be > 0.
    - tarifas: optional list; if provided replaces existing detail rows.
      Empty list = clear all tarifas (raises error since at least one is needed).
      None = preserve current tariff configuration.
    - Only editable when estado == PENDIENTE.
    """
    valor_declarado: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo valor declarado (opcional, preserva actual si se omite)",
    )
    tarifas: Optional[List[TarifaPatchIn]] = Field(
        None,
        description="Lista de tarifas a aplicar (opcional, preserva actual si se omite). Lista vacia = sin tarifas (error).",
    )


# ── Wrapper schema (liquidacion_general + liquidacion_tipo) ──────────────────

class LiquidacionPatchPOGeneralIn(BaseSchema):
    """
    Partial update schema for general fields inside PO PATCH wrapper.

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


class LiquidacionPatchPODatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for PO PATCH."""
    valor_declarado: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo valor declarado (opcional, preserva actual si se omite)",
    )
    tipo_tramite: Optional[str] = Field(
        None,
        description="Tipo de trámite de edificaciones (ej. OBRA_NUEVA, AMPLIACION) — opcional",
    )


class LiquidacionPatchPOTarifasIn(BaseSchema):
    """
    Tarifa entries for liquidacion_tipo.tarifas in PO PATCH wrapper.
    Uses the same field names as creation (tarifa_porcentaje_obra_id, especialidad_id).
    """
    tarifa_porcentaje_obra_id: uuid.UUID = Field(..., description="ID of the TarifaPorcentajeObra")
    especialidad_id: uuid.UUID = Field(..., description="ID of the especialidad")


class LiquidacionPatchPOTipoIn(BaseSchema):
    """
    liquidacion_tipo wrapper for PO PATCH — mirrors creation structure.

    All fields optional — omitted fields preserve current stored values.
    """
    datos: Optional[LiquidacionPatchPODatosIn] = Field(
        None,
        description="Datos del cálculo (valor_declarado)",
    )
    tarifas: Optional[List[LiquidacionPatchPOTarifasIn]] = Field(
        None,
        description="Lista de tarifas a aplicar (opcional, preserva actual si se omite)",
    )


class LiquidacionPatchPOWrapperIn(BaseSchema):
    """
    Wrapper PATCH input for PO types (Edificaciones, Impacto Vial, Taludes).

    Supports two input formats:
    1. Wrapper (current/recommended): liquidacion_general + liquidacion_tipo
    2. Flat (legacy/backward compat): valor_declarado + tarifas directly at top level

    Both wrappers are optional; only provided fields are updated.
    The state guard (PENDIENTE) applies to both general and tipo updates.
    PAGADA blocks the entire PATCH regardless of which wrapper is provided.

    When both wrapper and flat fields are provided, wrapper takes precedence.
    """
    # Wrapper format (recommended)
    liquidacion_general: Optional[LiquidacionPatchPOGeneralIn] = Field(
        None,
        description="Campos generales opcionales (expediente, proyecto, municipalidad, etc.)",
    )
    liquidacion_tipo: Optional[LiquidacionPatchPOTipoIn] = Field(
        None,
        description="Campos de cálculo tipo PO opcionales (datos, tarifas) — estilo creación",
    )
    # Flat format (legacy/backward compat)
    valor_declarado: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo valor declarado (flat legacy format, opcional)",
    )
    tarifas: Optional[List[TarifaPatchIn]] = Field(
        None,
        description="Lista de tarifas a aplicar (flat legacy format, opcional)",
    )
