"""
Liquidacion Edificacion — Edificacion-specific liquidacion extension.

Este archivo contiene el modelo de detalle para liquidaciones de edificacion.
La clase se llama LiquidacionEdificacion (singular) segun el contrato.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from .liquidacion import LiquidacionGeneral
from ...constants import TipoTramiteEdificaciones, TramiteAccion


class LiquidacionEdificacion(BaseModel):
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

    public_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID Público",
        help_text="Identificador público de la liquidación de edificaciones (ej. E-2026-00001).",
    )

    tipo_tramite = models.CharField(
        max_length=30,
        choices=TipoTramiteEdificaciones.choices,
        default=TipoTramiteEdificaciones.OBRA_NUEVA,
        verbose_name="Tipo de Trámite",
    )

    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        default=TramiteAccion.PRIMERA_REVISION,
        verbose_name="Acción de Trámite",
    )

    class Meta:
        verbose_name = "Liquidación de Edificación"
        verbose_name_plural = "Liquidaciones de Edificaciones"

    def __str__(self):
        return f"Edificación {self.liquidacion}"


class LiquidacionEdificacionProxy(LiquidacionGeneral):
    """
    Proxy model para el régimen de Edificaciones.
    Comparte el mismo DB table que LiquidacionGeneral, pero expone un admin
    dedicado con el inline de LiquidacionEdificacion pre-configurado.
    """

    class Meta:
        proxy = True
        verbose_name = "Liquidación Edificación"
        verbose_name_plural = "Liquidaciones Edificaciones"
