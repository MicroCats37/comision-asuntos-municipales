"""
Liquidación de Inspección de Obra — extensión de liquidación específica para inspección de obra.

Este archivo contiene el modelo de detalle para liquidaciones de inspección de obra.
La clase se llama LiquidacionInspeccionObra (singular) según el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.constants import TramiteAccion


class LiquidacionInspeccionObra(BaseModel, AutoNumeroModel):
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

    class Meta:
        verbose_name = "Liquidación de Inspección de Obra"
        verbose_name_plural = "Liquidaciones de Inspección de Obra"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Inspección de Obra {self.liquidacion}"
