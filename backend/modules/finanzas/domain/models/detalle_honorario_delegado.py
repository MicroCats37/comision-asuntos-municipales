# -*- coding: utf-8 -*-
"""
DetalleHonorarioDelegado — Detalle (parcial por liquidacion) de un RH mensual del delegado.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class DetalleHonorarioDelegado(BaseModel):
    """
    Detalle por LiquidacionDelegado de un ReciboHonorarioDelegadoMensual.

    El imp_bruto se extrae del LiquidacionPorcentajeObraDetalle cuya
    especialidad coincide con la especialidad_revision de la LiquidacionDelegado.
    """

    history = HistoricalRecords()

    recibo_mensual = models.ForeignKey(
        "ReciboHonorarioDelegadoMensual",
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Recibo Mensual",
    )
    liquidacion_delegado = models.ForeignKey(
        "liquidaciones.LiquidacionDelegado",
        on_delete=models.PROTECT,
        related_name="detalles_honorario",
        verbose_name="Liquidacion Delegado",
    )
    imp_bruto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Importe Bruto (del detalle porcentual)",
    )

    class Meta:
        verbose_name = "Detalle de Honorario del Delegado"
        verbose_name_plural = "Detalles de Honorarios del Delegado"
        ordering = ["recibo_mensual", "liquidacion_delegado"]

    def __str__(self):
        return f"Detalle {self.recibo_mensual_id} - {self.liquidacion_delegado_id}"
