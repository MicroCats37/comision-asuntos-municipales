"""
LiquidacionInspector - tabla explicita entre LiquidacionGeneral e Inspector.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.liquidaciones.domain.constants import DictamenRevision


class LiquidacionInspector(BaseModel):
    """Relacion muchos-a-muchos entre LiquidacionGeneral e Inspector."""

    history = HistoricalRecords()

    liquidacion = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="liquidacion_inspectores",
        verbose_name="Liquidacion",
    )
    inspector = models.ForeignKey(
        "Inspector",
        on_delete=models.PROTECT,
        related_name="liquidacion_inspectores",
        verbose_name="Inspector",
    )
    periodo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Periodo")
    dictamen_revision = models.CharField(
        max_length=20,
        choices=DictamenRevision.choices,
        blank=True,
        null=True,
        verbose_name="Dictamen de Revision",
    )
    fecha_presentacion = models.DateField(blank=True, null=True, verbose_name="Fecha de Presentacion")
    fecha_revision = models.DateField(blank=True, null=True, verbose_name="Fecha de Revision")

    class Meta:
        verbose_name = "Inspector de Liquidacion"
        verbose_name_plural = "Inspectores de liquidaciones"
        ordering = ["liquidacion", "inspector"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "inspector"],
                name="unique_liquidacion_inspector",
            ),
        ]

    def __str__(self):
        return f"{self.inspector} @ Liquidacion {self.liquidacion.public_id or self.liquidacion_id}"
