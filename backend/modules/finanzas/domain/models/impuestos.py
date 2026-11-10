"""
IGV / UIT / Derecho Mínimo — Constantes financieras.
"""

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel, VigenciaQuerySet
from core_application.vigencia import (
    SCOPE_GLOBAL,
    exclusion_constraint_vigencia,
    vigencia_rango_valido_constraint,
)


class IGVQuerySet(VigenciaQuerySet):
    """QuerySet para IGV — hereda la lógica de vigencia común de VigenciaQuerySet."""
    pass


class UITQuerySet(VigenciaQuerySet):
    """QuerySet para UIT — hereda la lógica de vigencia común de VigenciaQuerySet."""
    pass


class IGV(BaseModel, VigenciaModel):
    """
    Tasa de IGV (Impuesto General a las Ventas) aplicable a liquidaciones.
    Almacenada como fracción decimal (ej. 0.18 = 18%).
    Puede tener vigencia limitada (periodo_fin null = vigente).
    """

    objects = IGVQuerySet.as_manager()

    history = HistoricalRecords()

    # Scope key: the IGV rate is global (one schedule for the whole municipality).
    vigencia_scope_fields = SCOPE_GLOBAL

    valor = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
        verbose_name="Tasa IGV",
        help_text="Tasa de IGV como fracción decimal (ej. 0.18 para 18%)",
    )

    class Meta:
        verbose_name = "IGV"
        verbose_name_plural = "IGV"
        ordering = ["-periodo_inicio"]
        constraints = [
            vigencia_rango_valido_constraint("igv"),
            exclusion_constraint_vigencia(
                SCOPE_GLOBAL,
                name="exclude_igv_overlap",
            ),
        ]

    def __str__(self):
        porcentaje = float(self.valor) * 100
        return f"IGV {porcentaje:.2f}% desde {self.periodo_inicio}"

    @property
    def vigente(self):
        """Retorna True si el registro está vigente (sin fecha de fin)."""
        return self.periodo_fin is None


class UIT(BaseModel, VigenciaModel):
    """
    Valor de UIT (Unidad Impositiva Tributaria) en soles.
    Es un valor monetario entero, no un porcentaje.
    Puede tener vigencia limitada (periodo_fin null = vigente).
    """

    objects = UITQuerySet.as_manager()

    history = HistoricalRecords()

    # Scope key: the UIT value is global (one schedule for the whole municipality).
    vigencia_scope_fields = SCOPE_GLOBAL

    valor = models.IntegerField(
        verbose_name="Valor UIT (S/)",
        help_text="Valor de la UIT en soles",
    )

    class Meta:
        verbose_name = "UIT"
        verbose_name_plural = "UIT"
        ordering = ["-periodo_inicio"]
        constraints = [
            vigencia_rango_valido_constraint("uit"),
            exclusion_constraint_vigencia(
                SCOPE_GLOBAL,
                name="exclude_uit_overlap",
            ),
        ]

    def __str__(self):
        return f"UIT S/ {self.valor} desde {self.periodo_inicio}"

    @property
    def vigente(self):
        """Retorna True si el registro está vigente (sin fecha de fin)."""
        return self.periodo_fin is None


