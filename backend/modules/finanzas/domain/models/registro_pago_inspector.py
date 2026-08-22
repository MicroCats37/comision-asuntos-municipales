# -*- coding: utf-8 -*-

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class RegistroPagoInspector(BaseModel):
    """Acumulado de inspecciones pagadas por liquidacion y periodo (no pagar doble)."""

    history = HistoricalRecords()

    liquidacion_por_categoria_visitas = models.ForeignKey(
        "liquidaciones.LiquidacionPorCategoriaVisitas",
        on_delete=models.PROTECT,
        related_name="registros_pago",
        verbose_name="Liquidacion de Categoria de Visitas",
    )
    periodo = models.CharField(max_length=7, verbose_name="Periodo (YYYY-MM)")
    inspecciones_pagadas = models.IntegerField(default=0, verbose_name="Inspecciones Pagadas")

    class Meta:
        verbose_name = "Registro de Pago del Inspector"
        verbose_name_plural = "Registros de Pago del Inspector"
        ordering = ["-periodo"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_por_categoria_visitas", "periodo"],
                name="unique_registro_pago_inspector",
            ),
        ]

    def __str__(self):
        return f"Registro {self.liquidacion_por_categoria_visitas_id} - {self.periodo}"
