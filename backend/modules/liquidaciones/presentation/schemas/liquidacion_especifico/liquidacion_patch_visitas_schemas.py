"""
PATCH input schemas for Visitas types (Inspeccion Obra).

Two input formats are supported:
1. Flat (legacy): `LiquidacionPatchVisitasIn` — direct calculation fields only.
2. Wrapper (current): `LiquidacionPatchVisitasWrapperIn` — `liquidacion_general` + `liquidacion_tipo`
   matching the creation contract structure.

Used by PATCH /liquidaciones/{type}/{id} endpoints for recalculating
calculation inputs (cantidad_visitas, categoria, tarifa_visitas_id) while
keeping the liquidacion in PENDIENTE state.
"""
import uuid
from typing import Optional

from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadUpdateSchema,
    ProyectoUpdateSchema,
)


class LiquidacionPatchVisitasIn(BaseSchema):
    """
    PATCH input for Visitas recalculation (flat/legacy format).

    All fields are optional — omitted fields preserve current stored values.

    Business rules:
    - cantidad_visitas: optional; if provided must be >= 1.
    - categoria: optional; if changed without explicit tarifa_visitas_id,
      the correct tariff for that categoria at fecha_registro will be looked up.
    - tarifa_visitas_id: optional; if provided must be vigente at fecha_registro.
    - Only editable when estado == PENDIENTE.
    """
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        description="Nueva cantidad de visitas (opcional, preserva actual si se omite)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (ej. A, B, C) (opcional, preserva actual si se omite)",
    )
    tarifa_visitas_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa de visitas a aplicar (opcional, preserva actual si se omite)",
    )


# ── Wrapper schema (liquidacion_general + liquidacion_tipo) ──────────────────

class LiquidacionPatchVisitasGeneralIn(BaseSchema):
    """
    Partial update schema for general fields inside Visitas PATCH wrapper.

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


class LiquidacionPatchVisitasDatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for Visitas PATCH."""
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        description="Nueva cantidad de visitas (opcional, preserva actual si se omite)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (ej. A, B, C) (opcional, preserva actual si se omite)",
    )


class LiquidacionPatchVisitasTarifaIn(BaseSchema):
    """Tarifa portion of liquidacion_tipo for Visitas PATCH."""
    tarifa_visitas_id: uuid.UUID = Field(..., description="ID de la tarifa de visitas a aplicar")


class LiquidacionPatchVisitasTipoIn(BaseSchema):
    """
    liquidacion_tipo wrapper for Visitas PATCH — mirrors creation structure.

    All fields optional — omitted fields preserve current stored values.
    """
    datos: Optional[LiquidacionPatchVisitasDatosIn] = Field(
        None,
        description="Datos del cálculo (cantidad_visitas, categoria)",
    )
    tarifa: Optional[LiquidacionPatchVisitasTarifaIn] = Field(
        None,
        description="Tarifa de visitas a aplicar",
    )
    inspector_operacion_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del InspectorOperacion a asociar (opcional, reemplaza el inspector existente)",
    )


class LiquidacionPatchVisitasWrapperIn(BaseSchema):
    """
    Wrapper PATCH input for Visitas types (Inspeccion Obra).

    Supports two input formats:
    1. Wrapper (current/recommended): liquidacion_general + liquidacion_tipo
    2. Flat (legacy/backward compat): cantidad_visitas + categoria + tarifa_visitas_id directly

    Both wrappers are optional; only provided fields are updated.
    The state guard (PENDIENTE) applies to both general and tipo updates.
    PAGADA blocks the entire PATCH regardless of which wrapper is provided.

    When both wrapper and flat fields are provided, wrapper takes precedence.
    """
    # Wrapper format (recommended)
    liquidacion_general: Optional[LiquidacionPatchVisitasGeneralIn] = Field(
        None,
        description="Campos generales opcionales (expediente, proyecto, municipalidad, etc.)",
    )
    liquidacion_tipo: Optional[LiquidacionPatchVisitasTipoIn] = Field(
        None,
        description="Campos de cálculo tipo Visitas opcionales (datos, tarifa) — estilo creación",
    )
    # Flat format (legacy/backward compat)
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        description="Nueva cantidad de visitas (flat legacy format, opcional)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (flat legacy format, opcional)",
    )
    tarifa_visitas_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa de visitas (flat legacy format, opcional)",
    )
