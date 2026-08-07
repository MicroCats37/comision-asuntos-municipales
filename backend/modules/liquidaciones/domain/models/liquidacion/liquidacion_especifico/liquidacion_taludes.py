"""
Liquidacion Taludes — taludes specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de taludes.
La clase se llama LiquidacionTaludes (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from .liquidacion import LiquidacionGeneral
from ...constants import TramiteAccion


class LiquidacionTaludes(BaseModel, AutoNumeroModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de taludes.
    Vincula la LiquidacionGeneral con el tipo de trámite de taludes.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo viven en LiquidacionPorMetroCuadrado.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="taludes",
        verbose_name="Liquidación",
    )

    class Meta:
        verbose_name = "Liquidación de Taludes"
        verbose_name_plural = "Liquidaciones de Taludes"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Taludes {self.liquidacion}"
