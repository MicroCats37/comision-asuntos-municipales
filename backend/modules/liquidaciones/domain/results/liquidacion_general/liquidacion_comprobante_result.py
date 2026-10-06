from pydantic import BaseModel
from typing import Optional


class LiquidacionComprobanteResult(BaseModel):
    """Domain result DTO for a liquidacion comprobante."""
    id: str
    tipo_comprobante: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    fecha_emision: Optional[str] = None
    monto: Optional[float] = None
    activo: bool = False
    motivo_reemplazo: Optional[str] = None