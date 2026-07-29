"""
Liquidacion Inspeccion Obra — inspección de obra specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de inspección de obra.
La clase se llama LiquidacionInspeccionObra (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import LiquidacionGeneral
from ...constants import TramiteAccion


class LiquidacionInspeccionObra(BaseModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de inspección de obra.
    Vincula la LiquidacionGeneral con el tipo de trámite de inspección de obra.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo viven en LiquidacionPorCategoriaVisitas.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="inspeccion_obra",
        verbose_name="Liquidación",
    )

    numero = models.PositiveIntegerField(
        verbose_name="Número de Liquidación",
        help_text="Número de liquidación asignado por el sistema.",
    )

    class Meta:
        verbose_name = "Liquidación de Inspección de Obra"
        verbose_name_plural = "Liquidaciones de Inspección de Obra"

    def __str__(self):
        return f"Inspección de Obra {self.liquidacion}"
