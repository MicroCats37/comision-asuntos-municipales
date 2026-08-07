"""
Liquidacion Habilitacion Urbana — habilitacion urbana specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de habilitacion urbana.
La clase se llama LiquidacionHabilitacionUrbana (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from .liquidacion import LiquidacionGeneral
from ...constants import TramiteAccion


class LiquidacionHabilitacionUrbana(BaseModel, AutoNumeroModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de habilitación urbana.
    Vincula la LiquidacionGeneral con el tipo de trámite de habilitación urbana.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo viven en LiquidacionPorMetroCuadrado.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="habilitacion_urbana",
        verbose_name="Liquidación",
    )

    class Meta:
        verbose_name = "Liquidación de Habilitación Urbana"
        verbose_name_plural = "Liquidaciones de Habilitaciones Urbanas"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Habilitación Urbana {self.liquidacion}"
