"""
Inspector — registro de inspector elegible para inspecciones de obra.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel
from modules.liquidaciones.domain.constants import DictamenRevision


class Inspector(BaseModel):
    
    perfil_ingeniero = models.OneToOneField(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="inspectores_liquidacion",
        verbose_name="Perfil de Ingeniero",
    )
    
    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="inspectores",
        verbose_name="Especialidad",
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = "Inspector"
        verbose_name_plural = "Inspectores"
        unique_together = ("perfil_ingeniero", "especialidad_revision")
        ordering = [
            "perfil_ingeniero__apellido_paterno",
            "perfil_ingeniero__apellido_materno",
            "perfil_ingeniero__nombres",
        ]

    def __str__(self):
        return f"{self.perfil_ingeniero.nombre_completo} (CIP: {self.perfil_ingeniero.cip})"


class InspectorTipoLiquidacion(BaseModel):
    """Catalogo de registros de inspectores por tipo de liquidacion."""

    history = HistoricalRecords()

    inspector = models.ForeignKey(
        "Inspector",
        on_delete=models.PROTECT,
        related_name="tipos_liquidacion",
        verbose_name="Inspector",
    )
    
    tipo_liquidacion = models.ForeignKey(
        "TipoLiquidacion",
        on_delete=models.PROTECT,
        related_name="inspectores",
        verbose_name="Tipo de Liquidación",
    )

    categoria = models.CharField(
        max_length=1,
        verbose_name="Numero de Registro",
    )

    numero_registro = models.CharField(
        max_length=50,
        verbose_name="Numero de Registro",
    )

    telefono = models.CharField(
        max_length=20,
        verbose_name="Telefono",
        blank=True,
        null=True,
    )
    email = models.EmailField(
        max_length=100,
        verbose_name="Correo Electronico",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Inspector"
        verbose_name_plural = "Inspectores"
        ordering = [
            "inspector__perfil_ingeniero__apellido_paterno",
            "inspector__perfil_ingeniero__apellido_materno",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["inspector", "tipo_liquidacion", "numero_registro"],
                name="unique_inspector_registro",
            ),
        ]

    def __str__(self):
        return f"{self.inspector.perfil_ingeniero.nombre_completo} ({self.tipo_liquidacion})"


class InspectorAsignacionPeriodo(BaseModel, VigenciaModel):
    """Vigencia periods for an Inspector assignment."""

    history = HistoricalRecords()

    inspector_tipo_liquidacion = models.ForeignKey(
        "InspectorTipoLiquidacion",
        on_delete=models.PROTECT,
        related_name="periodos",
        verbose_name="Inspector - Tipo de Liquidación",
    )


class LiquidacionInspector(BaseModel):
    """Relacion muchos-a-muchos entre LiquidacionGeneral e Inspector."""

    history = HistoricalRecords()
    liquidacion = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="liquidacion_inspectores",
        verbose_name="Liquidacion",
    )
    inspector = models.ForeignKey(
        "Inspector",
        on_delete=models.PROTECT,
        related_name="liquidacion_inspectores",
        verbose_name="Inspector",
    )
    periodo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Periodo"
    )
    dictamen_revision = models.CharField(
        max_length=20,
        choices=DictamenRevision.choices,
        blank=True,
        null=True,
        verbose_name="Dictamen de Revision",
    )
    fecha_presentacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Presentacion"
    )
    fecha_revision = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Revision"
    )

    class Meta:
        verbose_name = "Inspector de Liquidacion"
        verbose_name_plural = "Inspectores de liquidaciones"
        ordering = ["liquidacion", "inspector"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "inspector"], name="unique_liquidacion_inspector"
            ),
        ]

    def __str__(self):
        return f"{self.inspector} @ Liquidacion {self.liquidacion.id}"
