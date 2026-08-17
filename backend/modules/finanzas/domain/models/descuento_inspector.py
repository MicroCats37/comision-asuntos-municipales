"""
Escala de Descuentos del Inspector — modelo de dominio.

Escala con vigencia (como UIT/IGV) que define los rangos de monto y su
porcentaje de descuento para calcular los honorarios del inspector.

Rangos actuales (ej. escala 2026):
    monto < 8000       → 15%
    8000 <= monto < 15000 → 20%
    15000 <= monto < 30000 → 30%
    monto >= 30000     → 40%
"""

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel


class EscalaDescuentoInspector(BaseModel, VigenciaModel):
    """Escala de descuentos vigente para recibos de inspectores."""

    history = HistoricalRecords()

    nombre = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Nombre de la Escala",
    )

    class Meta:
        verbose_name = "Escala de Descuento del Inspector"
        verbose_name_plural = "Escalas de Descuento del Inspector"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"Escala {self.nombre or self.id} ({self.periodo_inicio})"


class RangoDescuentoInspector(BaseModel):
    """Rango de monto dentro de una escala con su porcentaje de descuento."""

    history = HistoricalRecords()

    escala = models.ForeignKey(
        "EscalaDescuentoInspector",
        on_delete=models.CASCADE,
        related_name="rangos",
        verbose_name="Escala",
    )

    monto_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto Mínimo",
    )

    monto_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Máximo (null = sin tope)",
    )

    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje de Descuento",
        help_text="Ej: 0.15 = 15%",
    )

    class Meta:
        verbose_name = "Rango de Descuento del Inspector"
        verbose_name_plural = "Rangos de Descuento del Inspector"
        ordering = ["escala", "monto_minimo"]
        constraints = [
            models.UniqueConstraint(
                fields=["escala", "monto_minimo"],
                name="unique_rango_descuento_inspector",
            ),
        ]

    def __str__(self):
        return (
            f"[{self.monto_minimo} - {self.monto_maximo or '∞'}] → "
            f"{self.porcentaje_descuento * 100:.1f}%"
        )

    def aplica_a(self, monto: Decimal) -> bool:
        """True si el monto cae dentro de este rango."""
        if monto < self.monto_minimo:
            return False
        if self.monto_maximo is not None and monto >= self.monto_maximo:
            return False
        return True
