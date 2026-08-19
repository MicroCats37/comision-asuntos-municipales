"""
Presenter for Impacto Vial (PorcentajeObra).

Inherits common logic from LiquidacionPorcentajeObraPresenter.
"""
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_porcentaje_obra_presenter import (
    LiquidacionPorcentajeObraPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_impacto_vial_schemas import (
    LiquidacionImpactoVialOutput,
    LiquidacionImpactoVialCotizarOutput,
    LiquidacionImpactoVialCotizarDetalleOut,
)


class LiquidacionImpactoVialPresenter(LiquidacionPorcentajeObraPresenter):
    """Concrete presenter for Impacto Vial tipo."""
    
    OUTPUT_SCHEMA = LiquidacionImpactoVialOutput
    COTIZAR_OUTPUT_SCHEMA = LiquidacionImpactoVialCotizarOutput
    COTIZAR_DETALLE_SCHEMA = LiquidacionImpactoVialCotizarDetalleOut
