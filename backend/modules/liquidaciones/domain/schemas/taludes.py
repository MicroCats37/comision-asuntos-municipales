"""
Domain schemas — Taludes.

Resultado de una liquidación de taludes.
No hereda de base class compartida.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class LiquidacionTaludesResult(BaseModel):
    """
    Resultado completo de una liquidación de taludes.

    Campos explícitos sin herencia de base class.
    """

    liquidacion_id: uuid.UUID
    liquidacion_public_id: str
    numero_revision: int
    estado: str
    fecha_creacion: str
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    proyecto_direccion: Optional[str]
    proyecto_entidad_id: Optional[uuid.UUID]
    proyecto_entidad_tipo: Optional[str]
    proyecto_entidad_nombre: Optional[str]
    proyecto_entidad_ruc: Optional[str]
    proyecto_valor_proyecto: Decimal = Decimal("0")
    municipalidad_id: uuid.UUID
    municipalidad_nombre: str
    expediente: Optional[str] = None
    observacion: Optional[str]
    igv_valor: Decimal
    uit_valor: Decimal
    totales_subtotal: Decimal
    totales_igv: Decimal
    totales_total_liquidacion: Decimal
    totales_total_a_pagar: Decimal
