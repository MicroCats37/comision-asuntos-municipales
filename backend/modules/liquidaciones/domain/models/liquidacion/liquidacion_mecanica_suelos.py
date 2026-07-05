"""
Liquidacion Mecanica Suelos — mecánica de suelos specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de mecánica de suelos.
La clase se llama LiquidacionMecanicaSuelos (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import LiquidacionGeneral
from ...constants import TramiteAccion


class LiquidacionMecanicaSuelos(BaseModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de mecánica de suelos.
    Vincula la LiquidacionGeneral con el tipo de trámite de mecánica de suelos.

    NOTA: numero_revision vive en LiquidacionGeneral, no aqui.
    Los valores de cálculo viven en LiquidacionPorMetroCuadrado.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="mecanica_suelos",
        verbose_name="Liquidación",
    )

    public_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID Público",
        help_text="Identificador público de la liquidación de mecánica de suelos (ej. MS-2026-00001).",
    )

    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        default=TramiteAccion.PRIMERA_REVISION,
        verbose_name="Acción de Trámite",
    )

    class Meta:
        verbose_name = "Liquidación de Mecánica de Suelos"
        verbose_name_plural = "Liquidaciones de Mecánica de Suelos"

    def __str__(self):
        return f"Mecánica de Suelos {self.liquidacion}"
