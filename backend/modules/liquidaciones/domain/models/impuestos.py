"""
IGV / UIT — Parámetros fiscales para liquidaciones.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Igv(BaseModel):
    """
    Porcentaje de IGV aplicable a liquidaciones.
    Puede tener vigencia limitada (fecha_fin null = vigente).
    """

    history = HistoricalRecords()

    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Porcentaje IGV",
    )
    fecha_inicio = models.DateField(
        verbose_name="Fecha de Inicio",
    )
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Fin",
    )

    class Meta:
        verbose_name = "IGV"
        verbose_name_plural = "IGV"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"IGV {self.porcentaje}% desde {self.fecha_inicio}"


class Uit(BaseModel):
    """
    Valor de UIT (Unidad Impositiva Tributaria) aplicable a liquidaciones.
    Puede tener vigencia limitada (fecha_fin null = vigente).
    """

    history = HistoricalRecords()

    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Porcentaje UIT",
    )
    fecha_inicio = models.DateField(
        verbose_name="Fecha de Inicio",
    )
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Fin",
    )

    class Meta:
        verbose_name = "UIT"
        verbose_name_plural = "UIT"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"UIT {self.porcentaje}% desde {self.fecha_inicio}"
