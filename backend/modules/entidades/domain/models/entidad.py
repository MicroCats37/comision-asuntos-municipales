"""
Entidad — Entidad maestra unificada para instituciones y personas naturales.
El tipo de documento (RUC/DNI) determina la semántica:
- RUC (11 dígitos) => institución
- DNI (8 dígitos) => persona natural
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel

# Opciones de tipo de documento
TIPO_DOCUMENTO_CHOICES = [
    ("RUC", "RUC"),
    ("DNI", "DNI"),
]

# Validador de RUC: exactamente 11 dígitos
ruc_validator = RegexValidator(
    regex=r"^\d{11}$",
    message="El RUC debe contener exactamente 11 dígitos numéricos.",
    code="invalid_ruc",
)

# Validador de DNI: exactamente 8 dígitos
dni_validator = RegexValidator(
    regex=r"^\d{8}$",
    message="El DNI debe contener exactamente 8 dígitos numéricos.",
    code="invalid_dni",
)


class EntidadManager(models.Manager):
    """Manager that filters to only active entities (removed activo field - all entities are now active by default)."""

    def get_queryset(self):
        return super().get_queryset()


class Entidad(BaseModel):
    """
    """

    history = HistoricalRecords()

    tipo_documento = models.CharField(
        max_length=3,
        choices=TIPO_DOCUMENTO_CHOICES,
        verbose_name="Tipo de Documento",
        help_text="RUC para instituciones, DNI para personas naturales.",
    )
    numero_documento = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        verbose_name="Número de Documento",
        help_text="RUC (11 dígitos) o DNI (8 dígitos).",
    )



    

    objects = models.Manager()
    active = EntidadManager()

    class Meta:
        verbose_name = "Entidad"
        verbose_name_plural = "Entidades"
        ordering = ["numero_documento"]

    def clean(self):
        if self.tipo_documento == "RUC" and not self.razon_social:
            raise ValidationError(
                {
                    "razon_social": "La razón social es requerida para instituciones (RUC)."
                }
            )
        if self.tipo_documento == "DNI" and not self.razon_social:
            raise ValidationError(
                {
                    "razon_social": "El nombre completo es requerido para personas naturales (DNI)."
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def es_institucion(self):
        """True if this is an institution (RUC)."""
        return self.tipo_documento == "RUC"

    @property
    def es_persona_natural(self):
        """True if this is a natural person (DNI)."""
        return self.tipo_documento == "DNI"

    @property
    def nombre_completo(self):
        """Full name: razon_social for both institutions and natural persons."""
        return self.razon_social or ""

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"

