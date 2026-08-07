"""
Liquidacion Edificacion — Edificacion-specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de edificacion.
La clase se llama LiquidacionEdificacion (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import AutoNumeroModel

from .liquidacion import LiquidacionGeneral
from ...constants import TipoTramiteEdificaciones, TramiteAccion


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

    tipo_tramite = models.CharField(
        max_length=30,
        choices=TipoTramiteEdificaciones.choices,
        default=TipoTramiteEdificaciones.OBRA_NUEVA,
        verbose_name="Tipo de Trámite",
        null=True,
        blank=True,
        help_text="Tipo de trámite de edificación: obra nueva, ampliación, remodelación, demolición, etc.",
    )

    class Meta:
        verbose_name = "Liquidación de Edificación"
        verbose_name_plural = "Liquidaciones de Edificaciones"
        ordering = ["liquidacion", "numero"]

    def __str__(self):
        return f"Edificación {self.liquidacion}"
