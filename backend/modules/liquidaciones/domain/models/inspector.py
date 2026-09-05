"""
Inspector — registro de inspector elegible para inspecciones de obra.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel
from modules.liquidaciones.domain.constants import DictamenRevision, CategoriaIO


class Inspector(BaseModel):

    history = HistoricalRecords()

    perfil_ingeniero = models.OneToOneField(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="inspectores_liquidacion",
        verbose_name="Perfil de Ingeniero",
    )
    
    class Meta:
        verbose_name = "Inspector"
        verbose_name_plural = "Inspectores"
        ordering = [
            "perfil_ingeniero__apellido_paterno",
            "perfil_ingeniero__apellido_materno",
            "perfil_ingeniero__nombres",
        ]

    def __str__(self):
        return f"{self.perfil_ingeniero.nombre_completo} (CIP: {self.perfil_ingeniero.cip})"


class InspectorOperacion(BaseModel):
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
        related_name="inspectores_operacion",
        verbose_name="Tipo de Liquidación",
    )

    categoria = models.CharField(
        max_length=1,
        choices=CategoriaIO.choices,
        verbose_name="Categoría",
    )

    numero_registro = models.CharField(
        max_length=50,
        verbose_name="Número de Registro",
    )

    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="inspectores_operacion",
        verbose_name="Especialidad",
    )

    @property
    def cip_sin_ceros(self):
        return self.inspector.perfil_ingeniero.cip_sin_ceros

    @property
    def email(self):
        return self.inspector.perfil_ingeniero.correo_personal

    @property
    def telefono(self):
        return self.inspector.perfil_ingeniero.celular

    def save(self, *args, **kwargs):
        # Keep numero_registro in sync with cip_sin_ceros and categoria
        self.numero_registro = f"CAM{self.cip_sin_ceros}{self.categoria}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Inspector de Operación"
        verbose_name_plural = "Inspectores de Operaciones"
        ordering = [
            "inspector__perfil_ingeniero__apellido_paterno",
            "inspector__perfil_ingeniero__apellido_materno",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["inspector", "tipo_liquidacion", "numero_registro"],
                name="unique_inspector_operacion_registro",
            ),
        ]

    def __str__(self):
        return f"{self.inspector.perfil_ingeniero.nombre_completo} ({self.tipo_liquidacion})"


class InspectorOperacionPeriodo(BaseModel, VigenciaModel):
    """Vigencia periods for an Inspector operation assignment."""

    history = HistoricalRecords()

    inspector_tipo_liquidacion = models.ForeignKey(
        "InspectorOperacion",
        on_delete=models.PROTECT,
        related_name="periodos",
        verbose_name="Inspector - Tipo de Liquidación",
    )

    class Meta:
        verbose_name = "Periodo de Inspector de Operación"
        verbose_name_plural = "Periodos de Inspector de Operaciones"
        ordering = ["inspector_tipo_liquidacion", "-periodo_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["inspector_tipo_liquidacion"],
                condition=models.Q(periodo_fin__isnull=True),
                name="unique_inspector_operacion_vigente",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.periodo_fin is None:
            existe_abierto = (
                InspectorOperacionPeriodo.objects
                .filter(inspector_tipo_liquidacion=self.inspector_tipo_liquidacion, periodo_fin__isnull=True)
                .exclude(pk=self.pk)
                .exists()
            )
            if existe_abierto:
                raise ValueError(
                    f"Ya existe un periodo abierto para este {self.inspector_tipo_liquidacion}. "
                    "Cierre el periodo actual antes de abrir uno nuevo."
                )
        super().save(*args, **kwargs)

    @classmethod
    def close_current_and_open_new(cls, inspector_tipo_liquidacion, fecha_inicio):
        """Cierra el periodo abierto (periodo_fin = fecha_inicio - 1 día) y crea uno nuevo."""
        from datetime import timedelta

        hoy = fecha_inicio - timedelta(days=1)
        cls.objects.filter(
            inspector_tipo_liquidacion=inspector_tipo_liquidacion,
            periodo_fin__isnull=True,
        ).update(periodo_fin=hoy)

        return cls.objects.create(
            inspector_tipo_liquidacion=inspector_tipo_liquidacion,
            periodo_inicio=fecha_inicio,
            periodo_fin=None,
        )


class LiquidacionInspector(BaseModel):
    """Relacion muchos-a-muchos entre LiquidacionPorCategoriaVisitas e Inspector.

    La IO es una liquidación especial: el inspector se asocia a la liquidación
    de TIPO (LiquidacionPorCategoriaVisitas — el cálculo por categoría de visitas),
    no a la LiquidacionGeneral.
    """

    history = HistoricalRecords()
    liquidacion = models.ForeignKey(
        "LiquidacionPorCategoriaVisitas",
        on_delete=models.CASCADE,
        related_name="inspectores",
        verbose_name="Liquidación por Categoría de Visitas",
    )
    inspector = models.ForeignKey(
        "Inspector",
        on_delete=models.PROTECT,
        related_name="liquidacion_inspectores",
        verbose_name="Inspector",
    )
    inspector_operacion = models.ForeignKey(
        "InspectorOperacion",
        on_delete=models.PROTECT,
        related_name="liquidaciones_inspector",
        verbose_name="Inspector de Operación",
        blank=True,
        null=True,
    )
    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="liquidacion_inspectores",
        verbose_name="Especialidad de Revisión",
    )
    periodo = models.PositiveSmallIntegerField(
        blank=True, null=True, verbose_name="Periodo (Año)",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    
    mes = models.PositiveSmallIntegerField(
        blank=True, null=True, verbose_name="Mes (1-12)",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
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
        verbose_name = "Inspector de Liquidación de Inspección de Obra"
        verbose_name_plural = "Inspectores de liquidaciones de Inspección de Obra"
        ordering = ["liquidacion", "inspector"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "inspector"], name="unique_liquidacion_inspector"
            ),
            models.CheckConstraint(
                check=models.Q(mes__isnull=True) | models.Q(mes__gte=1, mes__lte=12),
                name="liquidacion_inspector_mes_valid",
            ),
        ]

    def __str__(self):
        return f"{self.inspector} @ IO {self.liquidacion.id}"


# ── Backward-compatible aliases (to support existing service/orchestrator code during transition) ──
InspectorTipoLiquidacion = InspectorOperacion
InspectorAsignacionPeriodo = InspectorOperacionPeriodo
