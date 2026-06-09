"""
Liquidacion — Liquidación de pago a proyectistas.
"""

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Liquidacion(BaseModel):
    """
    Liquidación de pago asociada a un proyectista y una empresa.
    """

    history = HistoricalRecords()

    proyectista = models.ForeignKey(
        "Proyectista",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Proyectista",
    )
    empresa = models.ForeignKey(
        "entidades.Empresa",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Empresa",
    )
    igv = models.ForeignKey(
        "Igv",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="IGV",
    )
    uit = models.ForeignKey(
        "Uit",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="UIT",
    )
    valor_obra = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor de la Liquidación")

    derecho_minimo = models.DecimalField(max_digits=3, decimal_places=2, verbose_name="Derecho Mínimo")

    porcentaje = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Porcentaje Aplicado")
    
    class Meta:
        verbose_name = "Liquidación"
        verbose_name_plural = "Liquidaciones"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.proyectista} @ {self.empresa}"

    # ─── Propiedades calculadas visuales (no se guardan en DB) ───

    @property
    def monto_igv(self):
        """Monto IGV calculado: valor_obra * igv.porcentaje / 100."""
        if not self.valor_obra or not self.igv or not self.igv.porcentaje:
            return Decimal("0.00")
        return (self.valor_obra * self.igv.porcentaje) / Decimal("100")

    @property
    def monto_uit(self):
        """Monto UIT calculado: valor_obra * uit.porcentaje / 100."""
        if not self.valor_obra or not self.uit or not self.uit.porcentaje:
            return Decimal("0.00")
        return (self.valor_obra * self.uit.porcentaje) / Decimal("100")

    @property
    def total_calculado(self):
        """Total calculado: valor_obra + monto_igv + monto_uit."""
        if not self.valor_obra:
            return Decimal("0.00")
        return self.valor_obra + self.monto_igv + self.monto_uit