"""
Inspector — registro de inspector elegible para inspecciones de obra.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from ..constants import DelegadoStatus, TipoLiquidacion


class Inspector(BaseModel):
    """Catalogo de registros de inspectores por tipo de liquidacion."""

    history = HistoricalRecords()

    perfil_ingeniero = models.ForeignKey(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="inspectores_liquidacion",
        verbose_name="Perfil de Ingeniero",
    )
    especialidad = models.ForeignKey(
        "Especialidad",
        on_delete=models.PROTECT,
        related_name="inspectores",
        verbose_name="Especialidad",
    )
    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=(
            (TipoLiquidacion.EDIFICACION, "Edificacion"),
            (TipoLiquidacion.HABILITACION_URBANA, "Habilitacion Urbana"),
        ),
        verbose_name="Tipo de Liquidacion",
    )
    categoria = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Categoria",
    )
    numero_registro = models.CharField(
        max_length=50,
        verbose_name="Numero de Registro",
    )
    vigencia = models.DateField(verbose_name="Vigencia")
    status = models.CharField(
        max_length=20,
        choices=DelegadoStatus.choices,
        default=DelegadoStatus.ACTIVO,
        verbose_name="Estado",
    )

    class Meta:
        verbose_name = "Inspector"
        verbose_name_plural = "Inspectores"
        ordering = [
            "perfil_ingeniero__apellido_paterno",
            "perfil_ingeniero__apellido_materno",
            "especialidad__nombre",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["perfil_ingeniero", "tipo_liquidacion", "especialidad", "numero_registro"],
                name="unique_inspector_registro",
            ),
        ]

    def __str__(self):
        return f"{self.perfil_ingeniero.nombre_completo} - {self.especialidad} ({self.tipo_liquidacion})"
