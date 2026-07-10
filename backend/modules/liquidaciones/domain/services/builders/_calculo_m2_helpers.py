"""
Helpers de cálculo M2 — construyen DTOs de cálculo por metro cuadrado.

Este módulo contiene funciones puras que construyen TarifaM2CalculoData
y LiquidacionM2CalculoData a partir de modelos ORM.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from modules.liquidaciones.domain.schemas.shared import (
    TarifaM2CalculoData,
    LiquidacionM2CalculoData,
)


def _build_tarifa_m2_calculo_data(tarifa_m2) -> TarifaM2CalculoData:
    """
    Construye un TarifaM2CalculoData desde una instancia de tarifa M2.

    Args:
        tarifa_m2: Instancia de TarifaPorMetroCuadrado (ORM).

    Returns:
        TarifaM2CalculoData con los campos exactos del modelo.
    """
    return TarifaM2CalculoData(
        id=tarifa_m2.id,
        costo_por_m2=tarifa_m2.costo_por_m2,
        area_m2=tarifa_m2.area_m2,
        derecho_minimo=tarifa_m2.derecho_minimo,
        derecho_maximo=tarifa_m2.derecho_maximo,
    )


def _build_liquidacion_m2_calculo_data(
    liquidacion_m2,
    tarifa_data: TarifaM2CalculoData,
) -> LiquidacionM2CalculoData:
    """
    Construye un LiquidacionM2CalculoData desde una instancia de liquidación M2.

    Args:
        liquidacion_m2: Instancia de LiquidacionPorMetroCuadrado (ORM).
        tarifa_data: TarifaM2CalculoData construida previamente.

    Returns:
        LiquidacionM2CalculoData con los campos exactos del modelo.
    """
    return LiquidacionM2CalculoData(
        area_solicitada=liquidacion_m2.area_solicitada,
        area_base_calculo=liquidacion_m2.area_base_calculo,
        derecho=liquidacion_m2.derecho,
        tarifa=tarifa_data,
    )
