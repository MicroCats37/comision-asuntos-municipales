"""
Recibo de Honorarios del Inspector — modelo de dominio.

Generado desde una LiquidacionInspector (asociación IO + inspector + especialidad).
La matemática sigue la hoja de cálculo manual:

    a) importe_bruto          = sub_total de la LiquidacionGeneral (IO)
    b) inspecciones_programadas = cantidad_visitas de la LiquidacionPorCategoriaVisitas
    c) costo_por_inspeccion   = a / b
    d) inspecciones_mes       = input del usuario al crear el recibo
    e) monto_bruto            = c * d
    f) inspecciones_pagadas   = 0 (por ahora; histórico a definir)
    g) saldo_inspecciones     = b - d - f
    h) sub_total              = e
    i) descuento              = h * tasa_descuento_aplicada
    j) honorarios             = h - i

El porcentaje de descuento se obtiene de la EscalaDescuentoInspector vigente
según el sub_total (h).
"""

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class ReciboHonorarioInspector(BaseModel):
    """Recibo de honorarios del inspector generado desde una LiquidacionInspector."""

    history = HistoricalRecords()

    liquidacion_inspector = models.OneToOneField(
        "liquidaciones.LiquidacionInspector",
        on_delete=models.PROTECT,
        related_name="recibo_honorario",
        verbose_name="Asociación Inspector - IO",
    )

    escala_descuento = models.ForeignKey(
        "EscalaDescuentoInspector",
        on_delete=models.PROTECT,
        related_name="recibos",
        verbose_name="Escala de Descuento Aplicada",
    )

    # (b) Visitas programadas en la liquidación
    inspecciones_programadas = models.IntegerField(
        verbose_name="Inspecciones Programadas",
    )

    # (c) costo_por_inspeccion = importe_bruto / inspecciones_programadas
    costo_por_inspeccion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Costo por Inspección",
    )

    # (d) Input del usuario
    inspecciones_mes = models.IntegerField(
        verbose_name="Inspecciones del Mes",
    )

    # (e) monto_bruto = costo_por_inspeccion * inspecciones_mes
    monto_bruto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto Bruto del Mes",
    )

    # (f) Histórico de inspecciones ya pagadas (por ahora siempre 0)
    inspecciones_pagadas = models.IntegerField(
        default=0,
        verbose_name="Inspecciones Pagadas",
    )

    # (g) saldo_inspecciones = programadas - mes - pagadas
    saldo_inspecciones = models.IntegerField(
        verbose_name="Saldo de Inspecciones",
    )

    # (h) sub_total = monto_bruto
    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Sub Total",
    )

    # Tasa de descuento aplicada según la escala vigente (ej. 0.15)
    tasa_descuento_aplicada = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Tasa de Descuento Aplicada",
    )

    # (i) descuento = sub_total * tasa_descuento_aplicada
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Descuento",
    )

    # (j) honorarios = sub_total - descuento
    honorarios = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Honorarios a Pagar",
    )

    class Meta:
        verbose_name = "Recibo de Honorarios del Inspector"
        verbose_name_plural = "Recibos de Honorarios del Inspector"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"ReciboHonorarioInspector({self.liquidacion_inspector} - "
            f"{self.honorarios})"
        )
