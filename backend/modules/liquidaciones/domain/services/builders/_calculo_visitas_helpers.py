"""
Helpers de cálculo visitas — construyen DTOs de cálculo por categoría de visitas.

Este módulo contiene funciones puras que construyen TarifaVisitasCalculoData
y LiquidacionVisitasCalculoData a partir de modelos ORM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from modules.liquidaciones.domain.schemas.shared import (
    TarifaVisitasCalculoData,
    LiquidacionVisitasCalculoData,
)


def _build_tarifa_visitas_calculo_data(tarifa_visitas) -> TarifaVisitasCalculoData:
    """
    Construye un TarifaVisitasCalculoData desde una instancia de tarifa visitas.

    Args:
        tarifa_visitas: Instancia de TarifaPorCategoriaVisitas (ORM).

    Returns:
        TarifaVisitasCalculoData con los campos exactos del modelo.
    """
    return TarifaVisitasCalculoData(
        id=tarifa_visitas.id,
        costo_por_visita=tarifa_visitas.costo_por_visita,
        visitas_minimas=tarifa_visitas.visitas_minimas,
    )


def _build_liquidacion_visitas_calculo_data(
    liquidacion_visitas,
    tarifa_data: TarifaVisitasCalculoData,
) -> LiquidacionVisitasCalculoData:
    """
    Construye un LiquidacionVisitasCalculoData desde una instancia de liquidación visitas.

    Args:
        liquidacion_visitas: Instancia de LiquidacionPorCategoriaVisitas (ORM).
        tarifa_data: TarifaVisitasCalculoData construida previamente.

    Returns:
        LiquidacionVisitasCalculoData con los campos exactos del modelo.
    """
    return LiquidacionVisitasCalculoData(
        cantidad_visitas=liquidacion_visitas.cantidad_visitas,
        visitas_base_calculo=liquidacion_visitas.visitas_base_calculo,
        derecho=liquidacion_visitas.derecho,
        categoria=liquidacion_visitas.categoria,
        tarifa=tarifa_data,
    )
