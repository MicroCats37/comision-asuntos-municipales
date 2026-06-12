
from core.models import BaseModel
from simple_history.models import HistoricalRecords
from django.db import models

class Especialidad(BaseModel):
    
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
    
class EspecialidadPeriodo(BaseModel):
    
    history = HistoricalRecords()
    
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.CASCADE,
        related_name="especialidades_habilitadas",
        verbose_name="Especialidad",
    )
    habilitada = models.BooleanField(
        default=True,
        verbose_name="Habilitada",
    )
    periodo_inicio = models.DateField(
        blank=True,
        null=True,
        verbose_name="Inicio del Período",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fin del Período",
    )

    class Meta:
        verbose_name = "Especialidad Habilitada"
        verbose_name_plural = "Especialidades Habilitadas"