"""
Liquidacion Impacto Vial — impacto vial specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de impacto vial.
La clase se llama LiquidacionImpactoVial (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.constants import TramiteAccion


class LiquidacionImpactoVial(BaseModel, AutoNumeroModel):
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

    class Meta:
        verbose_name = "Liquidación de Impacto Vial"
        verbose_name_plural = "Liquidaciones de Impacto Vial"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Impacto Vial {self.liquidacion}"
