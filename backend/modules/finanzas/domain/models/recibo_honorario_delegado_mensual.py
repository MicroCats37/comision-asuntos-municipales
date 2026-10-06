# -*- coding: utf-8 -*-
"""
ReciboHonorarioDelegadoMensual — Maestra mensual del RH del delegado.

Agrupación mensual de recibos de honorarios del delegado, mirroring
ReciboHonorarioInspectorMensual. El imp_bruto viene de la suma de
LiquidacionPorcentajeObraDetalle que coincide con la especialidad_revision
de cada LiquidacionDelegado.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class ReciboHonorarioDelegadoMensual(BaseModel):
    """
    Maestra mensual del RH del delegado.

    A diferencia del inspector (que usa escala_descuento variable),
    aquí las tasas son FIJAS: 25% CIP, 5% CODEMU, 10% Fondo Común.
    """

    history = HistoricalRecords()

    delegado = models.ForeignKey(
        "liquidaciones.Delegado",
        on_delete=models.PROTECT,
        related_name="recibos_mensuales",
        verbose_name="Delegado",
    )
    delegado_operacion = models.ForeignKey(
        "liquidaciones.DelegadoOperacion",
        on_delete=models.PROTECT,
        related_name="recibos_mensuales",
        verbose_name="Delegado Operatividad",
        null=True,
        blank=True,
    )
    periodo = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Año del Periodo"
    )
    mes = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Mes del Periodo (1-12)"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Sub Total del Mes (suma de imp_bruto)",
    )
    renta_cip = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Renta CIP (25%)",
    )
    aporte_codemu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Aporte CODEMU (5%)",
    )
    fondo_comun = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Fondo Común (10%)",
    )
    neto_honorario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Neto Honorario",
    )
    numero = models.IntegerField(null=True, blank=True, verbose_name="Número de RH")
    tasa_delegado = models.ForeignKey(
        "TasaDelegado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Tasa Delegado",
    )

    class Meta:
        verbose_name = "Recibo de Honorarios Mensual del Delegado"
        verbose_name_plural = "Recibos de Honorarios Mensuales del Delegado"
        ordering = ["-periodo"]

    def __str__(self):
        return f"RH Delegado {self.delegado_id} - {self.periodo}-{self.mes:02d}" if self.periodo and self.mes else f"RH Delegado {self.delegado_id}"
