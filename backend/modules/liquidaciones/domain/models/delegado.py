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
    
    especialidad = models.ForeignKey(
        "especialidades.Especialidad",
        on_delete=models.PROTECT,
        related_name="delegados",
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

    class Meta:
        verbose_name = "Delegado"
        verbose_name_plural = "Delegados"
        ordering = ["perfil_ingeniero__apellido_paterno", "perfil_ingeniero__apellido_materno"]

    def __str__(self):
        return f"{self.perfil_ingeniero.nombre_completo} - {self.especialidad}"
    

class DistritoDelegado(BaseModel):
    """
    Modelo para asignar distritos específicos a un delegado.
    Un delegado puede tener múltiples distritos asignados.
    """

    history = HistoricalRecords()

    delegado = models.ForeignKey(
        Delegado,
        on_delete=models.CASCADE,
        related_name="distritos_asignados",
        verbose_name="Delegado",
    )
    distrito = models.CharField(
        max_length=100,
        validators=[validate_distrito],
        choices=get_district_choices(),
        verbose_name="Distrito Asignado",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Distrito del Delegado"
        verbose_name_plural = "Distritos de los Delegados"
        unique_together = ("delegado", "distrito")
        ordering = ["delegado__perfil_ingeniero__apellido_paterno", "delegado__perfil_ingeniero__apellido_materno", "distrito"]

    def __str__(self):
        return f"{self.delegado.perfil_ingeniero.nombre_completo} - {self.distrito}"
    

class PeriodoDelegado(BaseModel):
    """
    Modelo para asignar periodos específicos a un delegado.
    Un delegado puede tener múltiples periodos asignados.
    """

    history = HistoricalRecords()

    delegado = models.ForeignKey(
        Delegado,
        on_delete=models.CASCADE,
        related_name="periodos_asignados",
        verbose_name="Delegado",
    )
    inicio_periodo = models.DateField(verbose_name="Inicio del Periodo")
    fin_periodo = models.DateField(verbose_name="Fin del Periodo")

    class Meta:
        verbose_name = "Periodo del Delegado"
        verbose_name_plural = "Periodos de los Delegados"
        unique_together = ("delegado", "periodo")
        ordering = ["delegado__perfil_ingeniero__apellido_paterno", "delegado__perfil_ingeniero__apellido_materno", "periodo"]

    def __str__(self):
        return f"{self.delegado.perfil_ingeniero.nombre_completo} - {self.periodo}"