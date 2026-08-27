"""
Tasa de Delegado — modelo de dominio con vigencia.

Reemplaza las constantes TASA_RENTA_CIP, TASA_APORTE_CODEMU, TASA_FONDO_COMUN
en permite modificarlas sin cambios de código.
"""

from decimal import Decimal

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel


class TasaDelegadoQuerySet(models.QuerySet):
    """QuerySet personalizado para TasaDelegado."""

    def vigentes(self, fecha=None):
        """
        Retorna las tasas vigentes para una fecha dada.

        Args:
            fecha: Fecha a verificar. Defaults a today.

        Returns:
            QuerySet filtrado por vigencia.
        """
        from datetime import date

        if fecha is None:
            fecha = date.today()

        return self.filter(
            models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha),
            periodo_inicio__lte=fecha,
        )


class TasaDelegado(BaseModel, VigenciaModel):
    """
    Tasas de retención para Recibos de Honorarios del Delegado.

    Cada registro representa un período de vigencia con tasas específicas.
    Reemplaza las constantes TASA_RENTA_CIP, TASA_APORTE_CODEMU, TASA_FONDO_COMUN.
    """

    objects = TasaDelegadoQuerySet.as_manager()

    history = HistoricalRecords()

    nombre = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Nombre de la Tasa",
    )

    renta_cip = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("1")),
        ],
        verbose_name="Tasa Renta CIP",
        help_text="Fracción decimal (ej. 0.25 = 25%)",
    )

    aporte_codemu = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("1")),
        ],
        verbose_name="Tasa Aporte CODEMU",
        help_text="Fracción decimal (ej. 0.05 = 5%)",
    )

    fondo_comun = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("1")),
        ],
        verbose_name="Tasa Fondo Común",
        help_text="Fracción decimal (ej. 0.10 = 10%)",
    )

    class Meta:
        verbose_name = "Tasa de Delegado"
        verbose_name_plural = "Tasas de Delegado"
        ordering = ["-periodo_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["periodo_inicio"],
                condition=models.Q(periodo_fin__isnull=True),
                name="unique_tasa_delegado_vigente_periodo_inicio",
            ),
        ]

    def __str__(self):
        return f"TasaDelegado({self.periodo_inicio})"

    @property
    def vigente(self):
        """Retorna True si el registro está vigente (sin fecha de fin)."""
        return self.periodo_fin is None
