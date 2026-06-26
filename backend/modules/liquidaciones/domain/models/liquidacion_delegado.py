"""
LiquidacionDelegado - tabla explicita entre LiquidacionGeneral y Delegado.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.liquidaciones.domain.constants import DictamenRevision


class LiquidacionDelegado(BaseModel):
    """
    Relacion muchos-a-muchos entre LiquidacionGeneral y Delegado mediante tabla explicita.
    """

    history = HistoricalRecords()

    liquidacion = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="liquidacion_delegados",
        verbose_name="Liquidacion",
    )
    delegado = models.ForeignKey(
        "Delegado",
        on_delete=models.PROTECT,
        related_name="liquidacion_delegados",
        verbose_name="Delegado",
    )
    periodo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Periodo",
    )
    dictamen_revision = models.CharField(
        max_length=20,
        choices=DictamenRevision.choices,
        blank=True,
        null=True,
        verbose_name="Dictamen de Revision",
    )
    fecha_presentacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Presentacion",
    )
    fecha_revision = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Revision",
    )

    class Meta:
        verbose_name = "Delegado de Liquidacion"
        verbose_name_plural = "Delegados de liquidaciones"
        ordering = ["liquidacion", "delegado"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "delegado"],
                name="unique_liquidacion_delegado",
            ),
        ]

    def __str__(self):
        return f"{self.delegado} @ Liquidacion {self.liquidacion.public_id or self.liquidacion_id}"
