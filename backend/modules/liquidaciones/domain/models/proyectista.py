"""
Proyectista — Profesional que elabora los proyectos técnicos.
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

    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre",
    )

    class Meta:
        verbose_name = "Proyectista"
        verbose_name_plural = "Proyectistas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre