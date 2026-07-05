"""
Calculos Nuevos — modelos de cálculo para los nuevos formularios de liquidación.

Este archivo contiene los modelos de cálculo LiquidacionPorMetroCuadrado y
LiquidacionPorCategoriaVisitas que se conectan a LiquidacionGeneral.
"""

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import LiquidacionGeneral


class LiquidacionPorMetroCuadrado(BaseModel):
    """
    Cálculo por metro cuadrado de una liquidación.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    área solicitada, área base de cálculo (tras evaluar area_minima),
    derecho calculado con clamps aplicados, y referencia a la tarifa por m2 aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_m2",
        verbose_name="Liquidación General",
    )
    area_solicitada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Área Solicitada",
        help_text="Área total solicitada en metros cuadrados.",
    )
    area_base_calculo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Área Base de Cálculo",
        help_text="Área real aplicada tras evaluar area_minima (max(area_solicitada, area_minima)).",
    )
    derecho = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho",
        help_text="Monto del derecho calculado con clamps de derecho_minimo y derecho_maximo aplicados.",
    )
    tarifa_aplicada = models.ForeignKey(
        "TarifaPorMetroCuadrado",
        on_delete=models.RESTRICT,
        related_name="liquidaciones_m2",
        verbose_name="Tarifa Aplicada",
        help_text="Tarifa por metro cuadrado que se usó en este cálculo.",
    )

    class Meta:
        verbose_name = "Liquidación por Metro Cuadrado"
        verbose_name_plural = "Liquidaciones por Metro Cuadrado"

    def __str__(self):
        return f"Liquidación M2 {self.liquidacion_general}"


class LiquidacionPorCategoriaVisitas(BaseModel):
    """
    Cálculo por categoría de visitas de una liquidación de inspección de obra.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    cantidad de visitas solicitada, visitas base de cálculo (tras evaluar visitas_minimas),
    derecho calculado, categoría de inspección y referencia a la tarifa por categoría aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_visitas",
        verbose_name="Liquidación General",
    )
    cantidad_visitas = models.PositiveIntegerField(
        verbose_name="Cantidad de Visitas",
        help_text="Número de visitas de inspección solicitadas.",
    )
    visitas_base_calculo = models.PositiveIntegerField(
        default=0,
        verbose_name="Visitas Base de Cálculo",
        help_text="Cantidad de visitas usadas para el cálculo (max(cantidad_visitas, visitas_minimas)).",
    )
    derecho = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho",
        help_text="Monto del derecho calculado (= visitas_base_calculo * costo_por_visita).",
    )
    categoria = models.CharField(
        max_length=20,
        verbose_name="Categoría de Inspección",
        help_text="Categoría de inspección: A, B, C, etc.",
    )
    tarifa_aplicada = models.ForeignKey(
        "TarifaPorCategoriaVisitas",
        on_delete=models.RESTRICT,
        related_name="liquidaciones_visitas",
        verbose_name="Tarifa Aplicada",
        help_text="Tarifa por categoría de visitas que se usó en este cálculo.",
    )

    class Meta:
        verbose_name = "Liquidación por Categoría de Visitas"
        verbose_name_plural = "Liquidaciones por Categoría de Visitas"

    def __str__(self):
        return f"Liquidación Visitas {self.liquidacion_general}"
