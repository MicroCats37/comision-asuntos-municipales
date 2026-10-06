"""
Input schemas for cotizar-edicion endpoints.

cotizar-edicion is a READ-ONLY quote preview for editing an existing
liquidacion. It uses the liquidacion_tipo wrapper format only.

The key difference from normal /cotizar:
- Uses historical financial values (by LiquidacionGeneral.fecha_registro)
- Reads existing liquidacion by ID to get fecha_registro
- Does NOT persist any changes

Three engines:
- PO (PorcentajeObra): Edificaciones, Taludes, Impacto Vial
- M2 (PorMetroCuadrado): Habilitación Urbana, Mecánica de Suelos
- Visitas: Inspección de Obra
"""
import uuid
from decimal import Decimal
from typing import Optional, List

from ninja import Field
from core.types import BaseSchema


# ── PO (PorcentajeObra) Schemas ───────────────────────────────────────────────


class CotizarEdicionPODatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for PO cotizar-edicion."""
    valor_declarado: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Valor declarado para la cotización de edición",
    )


class CotizarEdicionPOTarifaIn(BaseSchema):
    """Tarifa entry for PO cotizar-edicion liquidacion_tipo.tarifas."""
    tarifa_porcentaje_obra_id: uuid.UUID = Field(
        ...,
        description="ID of the TarifaPorcentajeObra",
    )
    especialidad_id: uuid.UUID = Field(
        ...,
        description="ID of the especialidad",
    )


class CotizarEdicionPOTipoIn(BaseSchema):
    """
    liquidacion_tipo wrapper for PO cotizar-edicion.
    """
    datos: CotizarEdicionPODatosIn
    tarifas: List[CotizarEdicionPOTarifaIn] = Field(
        ...,
        description="Lista de tarifas aplicadas en la cotización de edición",
    )


class CotizarEdicionPOWrapperIn(BaseSchema):
    """
    Input for POST /liquidaciones/{tipo}/{id}/cotizar-edicion for PO types.

    Uses the liquidacion_tipo wrapper only (no liquidacion_general).

    Frontend flow:
    1. GET /liquidaciones/{tipo}/{id} → extracts fecha_registro from DB
    2. POST /liquidaciones/{tipo}/{id}/cotizar-edicion with edited values
    3. Backend uses DB fecha_registro (NOT user-provided) for historical resolution
    """
    liquidacion_tipo: CotizarEdicionPOTipoIn


# ── M2 (PorMetroCuadrado) Schemas ──────────────────────────────────────────────


class CotizarEdicionM2DatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for M2 cotizar-edicion."""
    area_solicitada: float = Field(
        ...,
        gt=0,
        description="Área solicitada en m2",
    )


class CotizarEdicionM2TarifaIn(BaseSchema):
    """Tarifa portion of liquidacion_tipo for M2 cotizar-edicion."""
    tarifa_m2_id: uuid.UUID = Field(
        ...,
        description="ID of the TarifaPorMetroCuadrado",
    )


class CotizarEdicionM2TipoIn(BaseSchema):
    """liquidacion_tipo wrapper for M2 cotizar-edicion."""
    datos: CotizarEdicionM2DatosIn
    tarifa: CotizarEdicionM2TarifaIn


class CotizarEdicionM2WrapperIn(BaseSchema):
    """
    Input for POST /liquidaciones/{tipo}/{id}/cotizar-edicion for M2 types.
    """
    liquidacion_tipo: CotizarEdicionM2TipoIn


# ── Visitas (Inspección de Obra) Schemas ───────────────────────────────────────


class CotizarEdicionVisitasDatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for Visitas cotizar-edicion."""
    cantidad_visitas: int = Field(
        ...,
        ge=1,
        description="Cantidad de visitas",
    )
    categoria: Optional[str] = Field(
        None,
        description="Categoría de visita (e.g., 'CATE_A', 'CATE_B'). Optional — "
                    "if omitted, the stored category is used.",
    )


class CotizarEdicionVisitasTarifaIn(BaseSchema):
    """Tarifa portion of liquidacion_tipo for Visitas cotizar-edicion."""
    tarifa_visitas_id: uuid.UUID = Field(
        ...,
        description="ID of the TarifaPorCategoriaVisitas",
    )


class CotizarEdicionVisitasTipoIn(BaseSchema):
    """liquidacion_tipo wrapper for Visitas cotizar-edicion."""
    datos: CotizarEdicionVisitasDatosIn
    tarifa: CotizarEdicionVisitasTarifaIn


class CotizarEdicionVisitasWrapperIn(BaseSchema):
    """
    Input for POST /liquidaciones/{tipo}/{id}/cotizar-edicion for Visitas types.
    """
    liquidacion_tipo: CotizarEdicionVisitasTipoIn
