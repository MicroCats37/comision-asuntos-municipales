from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class TipoLiquidacion(BaseModel):
    history = HistoricalRecords()
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tipo de Liquidación"
        verbose_name_plural = "Tipos de Liquidación"

    def __str__(self):
        return self.nombre
