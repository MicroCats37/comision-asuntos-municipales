"""
Presentation schemas for Impacto Vial (PorcentajeObra).

Input: 2 wrappers (general + especifica)
Output: 3 wrappers (general + especifica=identidad + tipo=cálculo)
"""
import uuid
from decimal import Decimal
from typing import Optional, List
from core.types import BaseSchema
from ninja import Field
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
    EspecialidadOut,
)


class LiquidacionTipoOutput(BaseSchema):
    """Output de identidad: solo id + numero."""
    id: uuid.UUID
    numero: Optional[int] = Field(None, description="Número secuencial correlativo de la especialidad")


class LiquidacionImpactoVialInput(BaseSchema):
    """Input: 2 wrappers."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionImpactoVialOutput(BaseSchema):
    """Output: 3 wrappers."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # identidad
    liquidacion_tipo: LiquidacionPorcentajeObraDatosOut  # cálculo


class LiquidacionImpactoVialCotizarInput(BaseSchema):
    """
    Input for /cotizar endpoint.

    Only liquidacion_especifica is needed (no liquidacion_general).
    """
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionImpactoVialCotizarTarifaOut(BaseSchema):
    """Tarifa applied in cotizacion."""
    tarifa_id: uuid.UUID
    porcentaje_aplicado: Decimal
    especialidad_id: uuid.UUID


class LiquidacionImpactoVialCotizarDetalleOut(BaseSchema):
    """Detalle of cotizacion."""
    tarifa_id: uuid.UUID
    especialidad: EspecialidadOut
    porcentaje_aplicado: Decimal
    subtotal: Decimal


class LiquidacionImpactoVialCotizarOutput(BaseSchema):
    """Output for /cotizar endpoint."""
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: uuid.UUID
    detalles: List[LiquidacionImpactoVialCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal

