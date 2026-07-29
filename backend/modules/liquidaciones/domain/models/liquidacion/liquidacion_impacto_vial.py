"""
Liquidacion Impacto Vial — impacto vial specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de impacto vial.
La clase se llama LiquidacionImpactoVial (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import LiquidacionGeneral
from ...constants import TramiteAccion


class LiquidacionImpactoVial(BaseModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de impacto vial.
    Vincula la LiquidacionGeneral con el tipo de trámite de impacto vial.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo viven en LiquidacionPorMetroCuadrado.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="impacto_vial",
        verbose_name="Liquidación",
    )

    numero = models.PositiveIntegerField(
        verbose_name="Número de Liquidación",
        help_text="Número de liquidación asignado por el sistema.",
    )

    class Meta:
        verbose_name = "Liquidación de Impacto Vial"
        verbose_name_plural = "Liquidaciones de Impacto Vial"

    def __str__(self):
        return f"Impacto Vial {self.liquidacion}"
