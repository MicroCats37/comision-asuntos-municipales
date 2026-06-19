"""
Proyectista — Modelo de profesional responsable de proyectos técnicos.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Proyectista(BaseModel):
    """
    Profesional responsable de elaborar los proyectos técnicos
    que se incluyen en las liquidaciones.
    """

    history = HistoricalRecords()

    nombres = models.CharField(
        max_length=255,
        verbose_name="Nombre",
    )
    apellidos = models.CharField(
        max_length=255,
        verbose_name="Apellidos",
    )
    cip = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        unique=True,
        verbose_name="CIP",
        help_text="Número de CIP (6 dígitos).",
    )
    dni = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        unique=True,
        verbose_name="DNI",
        help_text="Número de DNI (8 dígitos).",
    )
    cap = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="CAP",
        help_text="Número de CAP (6 dígitos).",
    )

    class Meta:
        verbose_name = "Proyectista"
        verbose_name_plural = "Proyectistas"
        ordering= ["nombres"]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
