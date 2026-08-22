# -*- coding: utf-8 -*-

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class DetalleHonorarioInspector(BaseModel):
    """Detalle (parcial por liquidacion) de un RH mensual del inspector."""

    history = HistoricalRecords()

    recibo_mensual = models.ForeignKey(
        "ReciboHonorarioInspectorMensual",
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Recibo Mensual",
    )
    liquidacion_por_categoria_visitas = models.ForeignKey(
        "liquidaciones.LiquidacionPorCategoriaVisitas",
        on_delete=models.PROTECT,
        related_name="detalles_honorario",
        verbose_name="Liquidacion de Categoria de Visitas",
    )
    inspecciones_liquidadas = models.IntegerField(verbose_name="Inspecciones Liquidadas")
    costo_por_inspeccion = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo por Inspeccion")
    monto_contribuido = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Contribuido")

    class Meta:
        verbose_name = "Detalle de Honorario del Inspector"
        verbose_name_plural = "Detalles de Honorarios del Inspector"
        ordering = ["recibo_mensual", "liquidacion_por_categoria_visitas"]

    def __str__(self):
        return f"Detalle {self.recibo_mensual_id} - {self.liquidacion_por_categoria_visitas_id}"
