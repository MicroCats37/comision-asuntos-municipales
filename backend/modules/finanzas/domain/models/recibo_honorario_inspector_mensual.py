# -*- coding: utf-8 -*-

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class ReciboHonorarioInspectorMensual(BaseModel):
    """Maestra mensual del RH del inspector."""

    history = HistoricalRecords()

    inspector = models.ForeignKey(
        "liquidaciones.Inspector",
        on_delete=models.PROTECT,
        related_name="recibos_mensuales",
        verbose_name="Inspector",
    )
    periodo = models.CharField(max_length=7, verbose_name="Periodo (YYYY-MM)")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    escala_descuento = models.ForeignKey(
        "EscalaDescuentoInspector",
        on_delete=models.PROTECT,
        related_name="recibos_mensuales",
        verbose_name="Escala de Descuento Aplicada",
    )
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Sub Total del Mes")
    descuento = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Descuento")
    honorarios = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Honorarios a Pagar")

    class Meta:
        verbose_name = "Recibo de Honorarios Mensual del Inspector"
        verbose_name_plural = "Recibos de Honorarios Mensuales del Inspector"
        ordering = ["-periodo"]
        constraints = [
            models.UniqueConstraint(fields=["inspector", "periodo"], name="unique_rh_inspector_mensual"),
        ]

    def __str__(self):
        return f"RH Inspector {self.inspector_id} - {self.periodo}"
