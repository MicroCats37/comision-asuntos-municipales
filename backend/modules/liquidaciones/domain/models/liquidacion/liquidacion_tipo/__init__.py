"""
LiquidacionTipo package — re-exports for the liquidacion_tipo domain models.

Contrato Django §4.1: `models.py` raiz es re-export puro y cada sub-paquete
de `domain/models/` expone sus modelos por aqui. La tabla de CONTINUIDAD de
visitas (`LiquidacionContinuidadVisitas`) se ancla a la LCV de la liquidacion
nueva (B) y por eso vive aqui, junto al resto de los modelos de calculo por
tipo de liquidacion.
"""

from .liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    LiquidacionContinuidadVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorcentajeObraAcumulacion,
)
from .tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
)

__all__ = [
    # Modelos de calculo
    "LiquidacionPorMetroCuadrado",
    "LiquidacionPorCategoriaVisitas",
    "LiquidacionContinuidadVisitas",
    "LiquidacionPorcentajeObra",
    "LiquidacionPorcentajeObraDetalle",
    "LiquidacionPorcentajeObraAcumulacion",
    # Tarifas y reglas
    "TarifaLiquidacionBase",
    "TarifaPorcentajeObra",
    "TarifaPorMetroCuadrado",
    "TarifaPorCategoriaVisitas",
]
