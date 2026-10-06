# -*- coding: utf-8 -*-

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class RegistroPagoInspector(BaseModel):
    """Registro de inspecciones pagadas por liquidacion y periodo."""

    history = HistoricalRecords()

    liquidacion_por_categoria_visitas = models.ForeignKey(
        "liquidaciones.LiquidacionPorCategoriaVisitas",
        on_delete=models.PROTECT,
        related_name="registros_pago",
        verbose_name="Liquidacion de Categoria de Visitas",
    )
    periodo = models.PositiveSmallIntegerField(
        verbose_name="Año del Periodo",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        blank=True,
        null=True,
    )
    mes = models.PositiveSmallIntegerField(
        verbose_name="Mes (1-12)",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        blank=True,
        null=True,
    )
    inspecciones_pagadas = models.IntegerField(default=0, verbose_name="Inspecciones Pagadas")
    fecha_registro = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Registro",
    )

    class Meta:
        verbose_name = "Registro de Pago del Inspector"
        verbose_name_plural = "Registros de Pago del Inspector"
        ordering = ["-periodo", "-mes"]

    def __str__(self):
        periodo_display = (
            f"{self.periodo}-{self.mes:02d}"
            if self.periodo and self.mes
            else f"{self.periodo or '?'}-{self.mes or '?'}"
        )
        return f"Registro {self.liquidacion_por_categoria_visitas_id} - {periodo_display}"
