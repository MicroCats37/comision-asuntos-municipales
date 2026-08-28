"""
Delegado — Ingeniero delegado que puede crear y revisar liquidaciones.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from core_application.models import VigenciaModel
from ..constants import TipoDelegado
from modules.liquidaciones.domain.constants import DictamenRevision


class Delegado(BaseModel):
    """
    Ingeniero delegado que puede crear y revisar liquidaciones.
    """

    history = HistoricalRecords()

    perfil_ingeniero = models.OneToOneField(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="delegados",
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


class DelegadoOperacion(BaseModel):
    """
    Modelo para asignar distritos específicos a un delegado.
    Un delegado puede tener múltiples distritos asignados.
    """

    history = HistoricalRecords()

    delegado = models.ForeignKey(
        "Delegado",
        on_delete=models.PROTECT,
        related_name="municipalidades_asignadas",
        verbose_name="Delegado",
    )

    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="delegados_operacion",
        verbose_name="Municipalidad",
    )

    liquidacion_revision = models.ForeignKey(
        "liquidaciones.TipoLiquidacion",
        on_delete=models.PROTECT,
        related_name="delegados_operacion",
        verbose_name="Tipo de Liquidación",
        null=True,
        blank=True,
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoDelegado.choices,
        default=TipoDelegado.TITULAR,
        verbose_name="Tipo de Delegado",
    )

    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="delegados_operacion",
        verbose_name="Especialidad",
    )

    @property
    def email(self):
        return self.delegado.perfil_ingeniero.correo_personal

    @property
    def telefono(self):
        return self.delegado.perfil_ingeniero.celular

    class Meta:
        verbose_name = "Delegado de Operación"
        verbose_name_plural = "Delegados de Operaciones"
        unique_together = ("delegado", "municipalidad", "liquidacion_revision")
        ordering = [
            "delegado__perfil_ingeniero__apellido_paterno",
            "delegado__perfil_ingeniero__apellido_materno",
            "municipalidad__nombre",
        ]

    def __str__(self):
        return f"{self.delegado.perfil_ingeniero.nombre_completo} - {self.municipalidad.nombre}"


class DelegadoOperacionPeriodo(BaseModel, VigenciaModel):
    history = HistoricalRecords()

    delegado_municipalidad = models.ForeignKey(
        "DelegadoOperacion",
        on_delete=models.CASCADE,
        related_name="periodos",
        verbose_name="Delegado Operación",
    )

    class Meta:
        verbose_name = "Periodo de Delegación de Operación"
        verbose_name_plural = "Periodos de Delegación de Operaciones"
        ordering = ["delegado_municipalidad", "-periodo_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["delegado_municipalidad"],
                condition=models.Q(periodo_fin__isnull=True),
                name="unique_delegado_operacion_vigente",
            ),
        ]

    def __str__(self):
        return (
            f"{self.delegado_municipalidad} "
            f"({self.periodo_inicio} - {self.periodo_fin or 'vigente'})"
        )

    def save(self, *args, **kwargs):
        if self.periodo_fin is None:
            existe_abierto = (
                DelegadoOperacionPeriodo.objects
                .filter(delegado_municipalidad=self.delegado_municipalidad, periodo_fin__isnull=True)
                .exclude(pk=self.pk)
                .exists()
            )
            if existe_abierto:
                raise ValueError(
                    f"Ya existe un periodo abierto para este {self.delegado_municipalidad}. "
                    "Cierre el periodo actual antes de abrir uno nuevo."
                )
        super().save(*args, **kwargs)

    @classmethod
    def close_current_and_open_new(cls, delegado_municipalidad, fecha_inicio):
        """Cierra el periodo abierto (periodo_fin = fecha_inicio - 1 día) y crea uno nuevo."""
        from datetime import timedelta

        hoy = fecha_inicio - timedelta(days=1)
        cls.objects.filter(
            delegado_municipalidad=delegado_municipalidad,
            periodo_fin__isnull=True,
        ).update(periodo_fin=hoy)

        return cls.objects.create(
            delegado_municipalidad=delegado_municipalidad,
            periodo_inicio=fecha_inicio,
            periodo_fin=None,
        )


class LiquidacionDelegado(BaseModel):
    """
    Tabla explicita entre LiquidacionGeneral y Delegado.
    """

    history = HistoricalRecords()
    
    liquidacion = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="liquidacion_delegados",
        verbose_name="Liquidacion",
    )
    
    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="liquidacion_delegados",
        verbose_name="Especialidad de Revision",
    )

    delegado = models.ForeignKey(
        "Delegado",
        on_delete=models.PROTECT,
        related_name="delegado_liquidacion",
        verbose_name="Delegado",
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

    numero_rh = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Orden/RH",
    )

    class Meta:
        verbose_name = "Delegado de Liquidacion"
        verbose_name_plural = "Delegados de liquidaciones"
        ordering = ["liquidacion", "delegado"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "delegado", "especialidad_revision"],
                name="unique_liquidacion_delegado_especialidad",
            ),
            models.CheckConstraint(
                check=models.Q(mes__isnull=True) | models.Q(mes__gte=1, mes__lte=12),
                name="liquidacion_delegado_mes_valid",
            ),
        ]

    def __str__(self):
        return f"{self.delegado} @ {self.liquidacion}"


# ── Backward-compatible aliases (to support existing service/orchestrator code during transition) ──
DelegadoMunicipalidad = DelegadoOperacion
DelegadoMunicipalidadPeriodo = DelegadoOperacionPeriodo
