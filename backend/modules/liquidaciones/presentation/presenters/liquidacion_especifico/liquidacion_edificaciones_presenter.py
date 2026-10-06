"""
Presenter for Edificaciones (PorcentajeObra).

Inherits common logic from LiquidacionPorcentajeObraPresenter.
"""
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_porcentaje_obra_presenter import (
    LiquidacionPorcentajeObraPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesOutput,
    LiquidacionEdificacionesCotizarOutput,
    LiquidacionEdificacionesCotizarDetalleOut,
)


class LiquidacionEdificacionesPresenter(LiquidacionPorcentajeObraPresenter):
    """Concrete presenter for Edificaciones tipo."""
    
    OUTPUT_SCHEMA = LiquidacionEdificacionesOutput
    COTIZAR_OUTPUT_SCHEMA = LiquidacionEdificacionesCotizarOutput
    COTIZAR_DETALLE_SCHEMA = LiquidacionEdificacionesCotizarDetalleOut
