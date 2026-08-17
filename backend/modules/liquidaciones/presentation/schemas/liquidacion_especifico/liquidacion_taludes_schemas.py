"""
Presentation schemas for Taludes (PorcentajeObra).

Input: 2 wrappers (general + especifica)
Output: 3 wrappers (general + especifica=identidad + tipo=cálculo)
"""
import uuid
from decimal import Decimal
from typing import Optional, List
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
)


class LiquidacionTipoOutput(BaseSchema):
    """Output de identidad: solo id + numero."""
    id: uuid.UUID
    numero: int


class LiquidacionTaludesInput(BaseSchema):
    """Input: 2 wrappers."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionTaludesOutput(BaseSchema):
    """Output: 3 wrappers."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # identidad
    liquidacion_tipo: LiquidacionPorcentajeObraDatosOut  # cálculo


class LiquidacionTaludesCotizarInput(BaseSchema):
    """
    Input for /cotizar endpoint.

    Only liquidacion_especifica is needed (no liquidacion_general).
    """
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionTaludesCotizarTarifaOut(BaseSchema):
    """Tarifa applied in cotizacion."""
    tarifa_id: uuid.UUID
    porcentaje_aplicado: Decimal
    especialidad_id: uuid.UUID


class LiquidacionTaludesCotizarDetalleOut(BaseSchema):
    """Detalle of cotizacion."""
    tarifa_id: uuid.UUID
    especialidad_id: uuid.UUID
    porcentaje_aplicado: Decimal
    subtotal: Decimal


class LiquidacionTaludesCotizarOutput(BaseSchema):
    """Output for /cotizar endpoint."""
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: uuid.UUID
    detalles: List[LiquidacionTaludesCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal

