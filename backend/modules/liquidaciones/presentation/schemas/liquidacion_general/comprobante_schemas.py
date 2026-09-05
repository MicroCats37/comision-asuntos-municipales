"""
Comprobante presentation schemas — Input/Output for LiquidacionComprobante.
"""
from core.types import BaseSchema
from ninja import Field
from typing import Optional
import uuid


class LiquidacionComprobanteOutput(BaseSchema):
    """Output schema for a liquidacion comprobante."""
    id: uuid.UUID = Field(..., description="ID del comprobante")
    tipo_comprobante: Optional[str] = Field(None, description="Tipo: FACTURA, BOLETA, NOTA_CREDITO, NOTA_DEBITO")
    serie: Optional[str] = Field(None, description="Serie del comprobante")
    numero: Optional[str] = Field(None, description="Número del comprobante")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión (ISO date)")
    monto: Optional[float] = Field(None, description="Monto del comprobante")
    activo: bool = Field(..., description="Indica si es el comprobante activo")
    motivo_reemplazo: Optional[str] = Field(None, description="Motivo de reemplazo")


class LiquidacionComprobanteCreateIn(BaseSchema):
    """
    Input schema for creating/replacing a comprobante on a liquidacion.

    Basic data fields only — no archivo/foto for now.
    File handling is deferred to a future package.
    """
    tipo_comprobante: str = Field(
        ...,
        description="Tipo: FACTURA, BOLETA, NOTA_CREDITO, NOTA_DEBITO",
    )
    serie: Optional[str] = Field(None, description="Serie del comprobante")
    numero: Optional[str] = Field(None, description="Número del comprobante")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión (YYYY-MM-DD)")
    monto: Optional[float] = Field(None, description="Monto del comprobante")
    motivo_reemplazo: Optional[str] = Field(
        None,
        description="Motivo por el cual se reemplaza el comprobante anterior",
    )