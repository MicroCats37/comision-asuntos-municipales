"""
Delegado — Ingeniero delegado que puede crear y revisar liquidaciones.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from ..constants import DelegadoStatus, TipoDelegado, CategoriaDelegado
from ..validators import validate_distrito
from utils.ubigeo_schema import get_district_choices


class Delegado(BaseModel):
    """
    Ingeniero delegado que puede crear y revisar liquidaciones.
    """

    history = HistoricalRecords()

    perfil_ingeniero = models.UniqueConstraint(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="proyectistas",
        verbose_name="Perfil de Ingeniero",
        help_text="Perfil que contiene los datos de identidad del ingeniero.",
    )

    class Meta:
        verbose_name = "Delegado"
        verbose_name_plural = "Delegados"
        ordering = [
            "perfil_ingeniero__apellido_paterno",
            "perfil_ingeniero__apellido_materno",
            "perfil_ingeniero__nombres",
        ]


class DelegadoMunicipalidad(BaseModel):
    """
    Modelo para asignar distritos específicos a un delegado.
    Un delegado puede tener múltiples distritos asignados.
    """

    history = HistoricalRecords()

    delegado = models.ForeignKey(
        "usuarios.Delegado",
        on_delete=models.PROTECT,
        related_name="delegado_liquidacion",
        verbose_name="Delegado",
    )

    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="delegados",
        verbose_name="Municipalidad",
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoDelegado.choices,
        default=TipoDelegado.TITULAR,
        verbose_name="Tipo de Delegado",
    )
    categoria = models.CharField(
        max_length=50,
        choices=CategoriaDelegado.choices,
        null=True,
        blank=True,
        verbose_name="Categoría del Delegado en Distintas Liquidaciones",
    )

    class Meta:
        verbose_name = "Municipalidad del Delegado"
        verbose_name_plural = "Municipalidades de los Delegados"
        unique_together = ("delegado", "municipalidad")
        ordering = [
            "delegado__perfil_ingeniero__apellido_paterno",
            "delegado__perfil_ingeniero__apellido_materno",
            "municipalidad__nombre",
        ]

    def __str__(self):
        return f"{self.delegado.perfil_ingeniero.nombre_completo} - {self.municipalidad.nombre}"


class DelegadoMunicipalidadPeriodo(BaseModel):
    
    history = HistoricalRecords()
    
    delegado_municipalidad = models.ForeignKey(
        "DelegadoMunicipalidad",
        on_delete=models.CASCADE,
        related_name="periodos",
        verbose_name="Delegado Municipalidad",
    )
    
    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )   

    periodo_fin = models.DateField(
        verbose_name="Periodo de Fin",
    )
    
    