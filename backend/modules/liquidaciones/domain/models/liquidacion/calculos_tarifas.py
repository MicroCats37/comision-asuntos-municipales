"""
Modelos de cálculo para especialidades M2 y visitas.

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

    area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Área Solicitada",
        help_text="Área total solicitada en metros cuadrados.",
    )

    costo_por_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Costo por M2",
        help_text="Costo por metro cuadrado en soles.",
    )

    derecho_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo del derecho calculado según la tarifa.",
    )

    derecho_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho Máximo",
        help_text="Monto máximo del derecho calculado según la tarifa.",
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
        default=1,
        min_value=1,
        verbose_name="Cantidad de Visitas",
        help_text="Número de visitas de inspección solicitadas.",
    )

    porcentaje_uit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0"),
        verbose_name="Porcentaje UIT",
        help_text="Porcentaje de la UIT que se aplica para calcular el derecho.",
    )

    categoria = models.CharField(
        max_length=20,
        verbose_name="Categoría de Inspección",
        help_text="Categoría de inspección: A, B, C, etc.",
    )

    class Meta:
        verbose_name = "Liquidación por Categoría de Visitas"
        verbose_name_plural = "Liquidaciones por Categoría de Visitas"

    def __str__(self):
        return f"Liquidación Visitas {self.liquidacion_general}"


class LiquidacionPorcentajeObra(BaseModel):
    """
    Cálculo porcentual de una liquidación de obra.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    valores del proyecto, y referencia a la tarifa porcentual aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="liquidacion_porcentaje_obra",
        verbose_name="Liquidación General",
    )

    valor_declarado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Valor del Proyecto",
        help_text="Valor total del proyecto de edificación.",
    )

    derecho_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo absoluto del derecho en soles.",
    )
    derecho_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo absoluto del derecho en soles (nulo = sin tope).",
    )
    porcentaje_minimo_uit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje Mínimo UIT",
        help_text="Mínimo como porcentaje de la UIT (protección para montos bajos).",
    )

    class Meta:
        verbose_name = "Liquidación Porcentual de Obra"
        verbose_name_plural = "Liquidaciones Porcentuales de Obra"

    def __str__(self):
        return f"Liquidación Porcentual {self.liquidacion_general}"
