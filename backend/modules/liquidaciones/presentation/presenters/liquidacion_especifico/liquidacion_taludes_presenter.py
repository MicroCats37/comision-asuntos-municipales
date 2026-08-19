"""
Presenter for Taludes (PorcentajeObra).

Inherits common logic from LiquidacionPorcentajeObraPresenter.
"""
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_porcentaje_obra_presenter import (
    LiquidacionPorcentajeObraPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_taludes_schemas import (
    LiquidacionTaludesOutput,
    LiquidacionTaludesCotizarOutput,
    LiquidacionTaludesCotizarDetalleOut,
)


class LiquidacionTaludesPresenter(LiquidacionPorcentajeObraPresenter):
    """Concrete presenter for Taludes tipo."""
    
    OUTPUT_SCHEMA = LiquidacionTaludesOutput
    COTIZAR_OUTPUT_SCHEMA = LiquidacionTaludesCotizarOutput
    COTIZAR_DETALLE_SCHEMA = LiquidacionTaludesCotizarDetalleOut
