"""
Revision — Revisión de una liquidación por un delegado.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Revision(BaseModel):
    """
    Revisión de una liquidación realizada por un delegado.
    El campo `numero` es incremental por liquidación y la constraint
    UniqueConstraint(liquidacion, numero) impide duplicados.
    """

    history = HistoricalRecords()

    liquidacion = models.ForeignKey(
        "Liquidacion",
        on_delete=models.CASCADE,
        related_name="revisiones",
        verbose_name="Liquidación",
    )
    numero = models.PositiveIntegerField(
        verbose_name="Número de Revisión",
        help_text="Número secuencial de revisión por liquidación. Se asigna automáticamente si se omite.",
    )

    class Meta:
        verbose_name = "Revisión"
        verbose_name_plural = "Revisiones"
        ordering = ["liquidacion", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "numero"],
                name="unique_liquidacion_revision_numero",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.numero or self.numero == 0:
            max_num = Revision.objects.filter(liquidacion=self.liquidacion).exclude(pk=self.pk).aggregate(models.Max("numero"))["numero__max"]
            self.numero = (max_num or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Revisión {self.numero} de {self.liquidacion}"