"""
Delegado — Ingeniero delegado que puede crear y revisar liquidaciones.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from ..constants import DelegadoStatus
from ..validators import validate_distrito
from utils.ubigeo_schema import get_district_choices


class Delegado(BaseModel):
    """
    Ingeniero con perfil profesional que actúa como delegado
    para la creación y revisión de liquidaciones.
    """

    history = HistoricalRecords()

    perfil_ingeniero = models.OneToOneField(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="delegado_liquidacion",
        verbose_name="Perfil de Ingeniero",
    )
    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="delegados",
        verbose_name="Municipalidad",
    )
    especialidad = models.CharField(
        max_length=200,
        verbose_name="Especialidad",
    )
    banco = models.ForeignKey(
        "entidades.Banco",
        on_delete=models.PROTECT,
        related_name="delegados",
        verbose_name="Banco",
    )
    status = models.CharField(
        max_length=20,
        choices=DelegadoStatus.choices,
        default=DelegadoStatus.ACTIVO,
        verbose_name="Estado",
    )
    distrito = models.CharField(
        max_length=200,
        choices=get_district_choices(),
        validators=[validate_distrito],
        verbose_name="Distrito",
        help_text="Distrito donde opera el delegado (validado contra ubigeo nacional). Formato: DEPARTAMENTO - PROVINCIA - DISTRITO.",
    )

    class Meta:
        verbose_name = "Delegado"
        verbose_name_plural = "Delegados"
        ordering = ["perfil_ingeniero__apellido_paterno", "perfil_ingeniero__apellido_materno"]

    def __str__(self):
        return f"{self.perfil_ingeniero.nombre_completo} - {self.especialidad}"