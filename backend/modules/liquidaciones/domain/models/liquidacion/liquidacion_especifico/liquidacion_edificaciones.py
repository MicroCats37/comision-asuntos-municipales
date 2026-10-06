"""
Liquidación de Edificación — extensión de liquidación específica para edificaciones.

Este archivo contiene el modelo de detalle para liquidaciones de edificación.
La clase se llama LiquidacionEdificacion (singular) según el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.constants import TipoTramiteEdificaciones, TramiteAccion


class LiquidacionEdificacion(BaseModel, AutoNumeroModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de edificaciones.
    Vincula la LiquidacionGeneral con el tipo de trámite de edificación.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo (valor_proyecto, valor_base_calculo) viven en LiquidacionPorcentajeObra.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="edificaciones",
        verbose_name="Liquidación",
    )



    class Meta:
        verbose_name = "Liquidación de Edificación"
        verbose_name_plural = "Liquidaciones de Edificaciones"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Edificación {self.liquidacion}"
