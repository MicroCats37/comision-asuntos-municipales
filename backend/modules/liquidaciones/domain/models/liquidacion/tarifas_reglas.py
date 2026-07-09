"""
Tarifas y Reglas — tarifas y reglas de resolución por especialidad.

Este archivo contiene:
- TarifaPorMetroCuadrado: tarifa por metro cuadrado con límites
- TarifaPorCategoriaVisitas: tarifa por categoría de visitas
- ReglaTarifaLiquidacion: regla genérica para resolver tarifa por tramite_accion
- ReglaTarifaInspeccionObra: regla específica para inspección de obra por categoria
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import TarifaLiquidacionBase
from ...constants import TramiteAccion


class TarifaPorMetroCuadrado(BaseModel):
    """
    Tarifa por metro cuadrado para liquidaciones de habilitación urbana,
    mecánica de suelos, impacto vial y taludes.

    Contiene el costo por m2, área mínima y los límites de derecho mínimo/máximo.

    Relación: Tiene OneToOneField hacia TarifaLiquidacionBase.
    Una TarifaPorMetroCuadrado pertenece a exactamente una TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    tarifa_base = models.OneToOneField(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="detalle_m2",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa por metro cuadrado.",
    )
    costo_por_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Costo por M2",
        help_text="Costo por metro cuadrado en soles.",
    )
    area_minima = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Área Mínima",
        help_text="Área mínima en metros cuadrados para el cálculo (se usa max(area_solicitada, area_minima)).",
    )
    derecho_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo absoluto del derecho en soles.",
    )
    derecho_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo absoluto del derecho en soles (nulo = sin tope).",
    )

    class Meta:
        verbose_name = "Tarifa por Metro Cuadrado"
        verbose_name_plural = "Tarifas por Metro Cuadrado"

    def __str__(self):
        return f"Tarifa M2 {self.costo_por_m2}/m2 (min: {self.derecho_minimo})"


class TarifaPorCategoriaVisitas(BaseModel):
    """
    Tarifa por categoría de visitas para liquidaciones de inspección de obra.

    Contiene el costo por visita y el número mínimo de visitas.

    Relación: Tiene OneToOneField hacia TarifaLiquidacionBase.
    Una TarifaPorCategoriaVisitas pertenece a exactamente una TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    tarifa_base = models.OneToOneField(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="detalle_visitas",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa por categoría de visitas.",
    )
    costo_por_visita = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Costo por Visita",
        help_text="Costo por cada visita de inspección en soles.",
    )
    visitas_minimas = models.PositiveIntegerField(
        verbose_name="Visitas Mínimas",
        help_text="Número mínimo de visitas para el cálculo (se usa max(cantidad_visitas, visitas_minimas)).",
    )

    class Meta:
        verbose_name = "Tarifa por Categoría de Visitas"
        verbose_name_plural = "Tarifas por Categoría de Visitas"

    def __str__(self):
        return f"Tarifa Visitas {self.costo_por_visita}/visita (mín: {self.visitas_minimas})"


class ReglaTarifaLiquidacion(BaseModel):
    """
    Regla genérica de resolución de tarifa para liquidaciones.

    Mapea una tarifa base a una combinación de tramite_accion.

    Una misma TarifaLiquidacionBase puede tener múltiples reglas
    (ej. para PRIMERA_REVISION y para REVISION).

    La combinación (tramite_accion, tarifa_base) debe ser única.

    NOTA: tipo_liquidacion NO está aquí porque ya está en TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        verbose_name="Acción de Trámite",
        help_text="Acción de trámite: PRIMERA_REVISION o REVISION.",
    )
    tarifa_base = models.ForeignKey(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="reglas_tarifa_liquidacion",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta regla.",
    )

    class Meta:
        verbose_name = "Regla de Tarifa de Liquidación"
        verbose_name_plural = "Reglas de Tarifas de Liquidación"
        ordering = ["tramite_accion"]
        constraints = [
            models.UniqueConstraint(
                fields=["tramite_accion", "tarifa_base"],
                name="unique_regla_tarifa_liquidacion",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tramite_accion"],
                name="idx_regla_liq_accion",
            ),
        ]

    def __str__(self):
        return f"Regla {self.tarifa_base.tipo_liquidacion}/{self.tramite_accion} -> {self.tarifa_base}"


class ReglaTarifaInspeccionObra(BaseModel):
    """
    Regla específica de resolución de tarifa para inspecciones de obra.

    Mapea una tarifa base a una combinación de categoria y tramite_accion.

    La combinación (categoria, tramite_accion, tarifa_base) debe ser única.
    """

    history = HistoricalRecords()

    categoria = models.CharField(
        max_length=20,
        verbose_name="Categoría de Inspección",
        help_text="Categoría de inspección de obra: A, B, C, etc.",
    )
    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        verbose_name="Acción de Trámite",
        help_text="Acción de trámite: PRIMERA_REVISION o REVISION.",
    )
    tarifa_base = models.ForeignKey(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="reglas_tarifa_inspeccion",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta regla.",
    )

    class Meta:
        verbose_name = "Regla de Tarifa de Inspección de Obra"
        verbose_name_plural = "Reglas de Tarifas de Inspección de Obra"
        ordering = ["categoria", "tramite_accion"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "tramite_accion", "tarifa_base"],
                name="unique_regla_tarifa_inspeccion",
            ),
        ]
        indexes = [
            models.Index(
                fields=["categoria", "tramite_accion"],
                name="idx_regla_insp_cat_accion",
            ),
        ]

    def __str__(self):
        return f"Regla Inspección {self.categoria}/{self.tramite_accion} -> {self.tarifa_base}"
