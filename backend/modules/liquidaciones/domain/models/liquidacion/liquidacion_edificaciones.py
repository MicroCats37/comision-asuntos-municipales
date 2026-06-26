"""
Liquidacion Edificaciones — Edificaciones-specific liquidacion classes and enums.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core.utils import esta_vigente

from .liquidacion import LiquidacionGeneral
from ...constants import TipoTramiteEdificaciones, TramiteAccion


class EdificacionesEspecialidades(BaseModel):
    """
    Define el grupo de especialidades vigentes para Liquidaciones de Edificaciones
    en un período determinado.

    Este modelo representa qué especialidades son válidas para el cálculo de
    liquidaciones de edificaciones en un momento dado. Se utiliza para validar
    que las revisiones seleccionadas en una liquidación representen exactamente
    el conjunto de especialidades vigentes.
    """

    history = HistoricalRecords()

    especialidades = models.ManyToManyField(
        "Especialidad",
        related_name="edificaciones_especialidades_grupo",
        verbose_name="Especialidades del Grupo",
    )

    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
    )

    class Meta:
        verbose_name = "Grupo de Especialidades de Edificación"
        verbose_name_plural = "Grupos de Especialidades de Edificación"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        fin_str = f" hasta {self.periodo_fin}" if self.periodo_fin else ""
        return f"Especialidades Edificación desde {self.periodo_inicio}{fin_str}"

    @property
    def habilitada(self):
        """Computado: determina si el grupo está vigente según el rango de fechas."""
        return esta_vigente(self.periodo_inicio, self.periodo_fin)


class EdificacionesTarifa(BaseModel):
    """
    Tarifas versionadas para cada clasificación de edificación.
    Contiene los campos de cálculo y vigencia (porcentaje_liquidacion,
    derecho mínimo/máximo, períodos).
    """

    history = HistoricalRecords()
    
    porcentaje_minimo_uit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje Mínimo UIT",
        help_text="Porcentaje del UIT que define el derecho mínimo.",
    )
    derecho_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo de derecho.",
    )
    derecho_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo de derecho (opcional).",
    )
    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
    )

    class Meta:
        verbose_name = "Tarifa de Edificación"
        verbose_name_plural = "Tarifas de Edificaciones"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"Tarifa Edificación desde {self.periodo_inicio}"


class EdificacionesRevision(BaseModel):
    """
    Revisión de tarifa de edificación con especialidades múltiples.

    Una revisión puede cubrir una o más especialidades (M2M), por ejemplo:
    arquitectura + estructuras + instalaciones sanitarias.
    El cálculo genera UN cargo por revisión, no por especialidad.
    """

    tarifa = models.ForeignKey(
        EdificacionesTarifa,
        on_delete=models.CASCADE,
        related_name="revisiones",
        verbose_name="Tarifa de Edificación",
    )

    porcentaje_liquidacion = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje de Liquidación",
        help_text="Porcentaje aplicado para el cálculo del derecho.",
    )

    especialidades = models.ManyToManyField(
        "Especialidad",
        related_name="edificaciones_revisiones",
        verbose_name="Especialidades",
    )

    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
    )

    class Meta:
        verbose_name = "Revisión de Edificación"
        verbose_name_plural = "Revisiones de Edificaciones"
        db_table = "liquidaciones_edificacionesrevision"

    def __str__(self):
        nombres = ", ".join(e.nombre for e in self.especialidades.all())
        return f"{nombres} - {self.tarifa}"

    @property
    def habilitada(self):
        return esta_vigente(self.periodo_inicio, self.periodo_fin)
class LiquidacionEdificaciones(BaseModel):
    """
    Perfil/extensión de una LiquidacionGeneral para el régimen de edificaciones.
    Vincula la LiquidacionGeneral con la tarifa de edificación aplicable.
    """

    history = HistoricalRecords()

    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="edificaciones",
        verbose_name="Liquidación",
    )
    
    numero_revision = models.PositiveIntegerField(
        default=0,
        verbose_name="Número de Revisión",
        help_text="Número secuencial de revisión por liquidación de edificaciones.",
    )

    public_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID Público",
        help_text="Identificador público de la liquidación de edificaciones (ej. LIQ-EDIF-2026-00001).",
    )

    # M2M a revisiones — una liquidación operativa puede seleccionar varias
    # revisiones aplicables.
    tipo_tramite = models.CharField(
        max_length=30,
        choices=TipoTramiteEdificaciones.choices,
        default=TipoTramiteEdificaciones.OBRA_NUEVA,
        verbose_name="Tipo de Trámite",
    )

    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        default=TramiteAccion.PRIMERA_REVISION,
        verbose_name="Acción de Trámite",
    )
    
    
    revisiones = models.ManyToManyField(
        EdificacionesRevision,
        related_name="liquidaciones_edificaciones",
        verbose_name="Revisiones de Edificación",
    )

    proyectistas = models.ManyToManyField(
        "Proyectista",
        related_name="liquidaciones_edificaciones",
        verbose_name="Proyectistas",
    )

    class Meta:
        verbose_name = "Liquidación de Edificaciones"
        verbose_name_plural = "Liquidaciones de Edificaciones"

    def __str__(self):
        return f"Edificaciones {self.liquidacion}"


class LiquidacionEdificacionesProxy(LiquidacionGeneral):
    """
    Proxy model para el régimen de Edificaciones.
    Comparte el mismo DB table que LiquidacionGeneral, pero expone un admin
    dedicado con el inline de LiquidacionEdificaciones pre-configurado.
    """

    class Meta:
        proxy = True
        verbose_name = "Liquidación Edificación"
        verbose_name_plural = "Liquidaciones Edificaciones"
