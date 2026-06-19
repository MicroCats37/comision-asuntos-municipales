from core.models import BaseModel
from simple_history.models import HistoricalRecords
from django.db import models


class Especialidad(BaseModel):
    """Catálogo de especialidades operative."""

    history = HistoricalRecords()

    nombre = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Nombre de la Especialidad",
    )

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"

    def __str__(self):
        return self.nombre