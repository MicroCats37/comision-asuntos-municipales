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
    inspector_operacion = models.ForeignKey(
        "liquidaciones.InspectorOperacion",
        on_delete=models.PROTECT,
        related_name="recibos_honorario_mensual",
        verbose_name="Inspector de Operación",
        blank=True,
        null=True,
    )
    numero = models.IntegerField(null=True, blank=True, verbose_name="Número de RH")
    periodo = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Año del Periodo"
    )
    mes = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Mes del Periodo (1-12)"
    )
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
    tasa_descuento = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Tasa de Descuento Aplicada",
    )

    class Meta:
        verbose_name = "Recibo de Honorarios Mensual del Inspector"
        verbose_name_plural = "Recibos de Honorarios Mensuales del Inspector"
        ordering = ["-periodo"]

    def __str__(self):
        return f"RH Inspector {self.inspector_id} - {self.periodo}-{self.mes:02d}" if self.periodo and self.mes else f"RH Inspector {self.inspector_id}"
