"""
Municipalidad — Entidad maestra de municipalidad.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Municipalidad(BaseModel):
    history = HistoricalRecords()
    """
    Entidad maestra de municipalidad.
    Representa gobiernos locales con los que interactúa el sistema CAM.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Código",
        help_text="Código único de la municipalidad.",
    )
    nombre = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Nombre",
    )
    alcalde = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Alcalde",
    )
    gerente_urbano = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Gerente Urbano",
    )
    telefono_contacto = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Teléfono de Contacto",
    )
    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Dirección",
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Municipalidad"
        verbose_name_plural = "Municipalidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class MunicipalidadContacto(BaseModel):
    history = HistoricalRecords()

    """
    Tabla puente que asocia un Contacto a una Municipalidad.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación municipalidad-contacto.
    """
    municipalidad = models.ForeignKey(
        Municipalidad,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Municipalidad",
    )
    contacto = models.ForeignKey(
        "Contacto",
        on_delete=models.PROTECT,
        related_name="municipalidades",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la municipalidad.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en la municipalidad.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Municipalidad - Contacto"
        verbose_name_plural = "Municipalidades - Contactos"
        ordering = ["-principal", "municipalidad__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipalidad", "contacto"],
                name="unique_municipalidad_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.municipalidad}"
