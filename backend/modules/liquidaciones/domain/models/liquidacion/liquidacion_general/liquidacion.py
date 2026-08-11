"""
LiquidacionGeneral — general liquidacion classes and enums.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from core_application.models import VigenciaModel
from modules.liquidaciones.domain.constants import (
    EstadoLiquidacion,
    TipoLiquidacion,
)


class LiquidacionGeneral(BaseModel):
    """
    Liquidación de pago a proyectistas para un proyecto.
    Representa la instancia operacional de liquidación/revisión de un proyecto.
    """

    history = HistoricalRecords()

    proyecto = models.ForeignKey(
        "Proyecto",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Proyecto",
    )

    especialidades_revisadas = models.ManyToManyField(
        "usuarios.Especialidad",
        related_name="liquidaciones_revisadas",
        verbose_name="Especialidades Revisadas",
        help_text="Especialidades que han sido revisadas en esta liquidación.",
    )

    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro",
        help_text="Fecha y hora en que se registró la liquidación en el sistema.",
    )

    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="liquidaciones_creadas",
        verbose_name="Usuario Creador",
        null=True,
        blank=True,
    )

    igv_id = models.ForeignKey(
        "finanzas.IGV",
        on_delete=models.PROTECT,
        verbose_name="IGV",
        blank=True,
        null=True,
    )

    uit_id = models.ForeignKey(
        "finanzas.UIT",
        on_delete=models.PROTECT,
        verbose_name="UIT",
        blank=True,
        null=True,
    )

    igv_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="IGV Snapshot",
        help_text="Valor del IGV en el momento del cálculo de la liquidación.",
        blank=True,
        null=True,
    )

    uit_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="UIT Snapshot",
        help_text="Valor de la UIT en el momento del cálculo de la liquidación.",
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoLiquidacion.choices,
        verbose_name="Estado de la Revisión",
        blank=True,
        null=True,
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total",
        help_text="Subtotal calculado de la liquidación . Se llena después del cálculo.",
    )

    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Sub Total",
        help_text="Subtotal calculado de la liquidación . Se llena después del cálculo.",
    )

    observacion = models.CharField(max_length=2000, null=True, blank=True)

    expediente = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Expediente",
        help_text="Número de expediente associated with the liquidacion.",
    )

    tipo_liquidacion = models.ForeignKey(
        'liquidaciones.TipoLiquidacion',
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario.",
    )

    numero_revision = models.PositiveIntegerField(
        default=1,
        verbose_name="Número de Revisión",
        help_text="Número secuencial de revisión (1 = primera revisión).",
    )

    liquidaciones_previas = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="revisiones",
        blank=True,
        verbose_name="Liquidaciones Previas",
        help_text="Referencias a liquidaciones anteriores en caso de revisiones sucesivas.",
    )
    
    retencion= models.BooleanField(
        default=False,
        verbose_name="¿Retención?",
        help_text="Indica si la liquidación tiene retención.",
    )

    class Meta:
        verbose_name = "Liquidación"
        verbose_name_plural = "Liquidaciones"
        ordering = ["proyecto", "-fecha_registro"]

    def __str__(self):
        return f"Liquidación de {self.proyecto}"


class LiquidacionCodigo(BaseModel):
    tipo_liquidacion = models.ForeignKey(
        'liquidaciones.TipoLiquidacion',
        on_delete=models.PROTECT,
        related_name='codigos',
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario.",
    )

    codigo_cta = models.CharField(
        max_length=20,
        verbose_name="Código de Cuenta",
        help_text="Código de cuenta asociado a la liquidación.",
    )

    class Meta:
        verbose_name = "Código de Liquidación"
        verbose_name_plural = "Códigos de Liquidaciones"
        ordering = ["tipo_liquidacion", "codigo_cta"]

    def __str__(self):
        return f"{self.tipo_liquidacion} - {self.codigo_cta}"


class LiquidacionContacto(BaseModel):
    """
    Tabla puente que asocia un Contacto a una Liquidación.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación liquidación-contacto.
    """

    liquidacion = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Liquidación",
    )
    contacto = models.ForeignKey(
        "entidades.Contacto",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=True,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la liquidación.",
    )

    class Meta:
        verbose_name = "Liquidación - Contacto"
        verbose_name_plural = "Liquidaciones - Contactos"
        ordering = ["-principal", "liquidacion__proyecto__denominacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "contacto"],
                name="unique_liquidacion_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.liquidacion}"


class LiquidacionDocumentos(BaseModel):
    """
    Documentos asociados a una LiquidacionGeneral, con su valor de obra.
    Se vincula a una LiquidacionGeneral y almacena los detalles de cada documento.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Liquidación General",
    )
    nombre_documento = models.CharField(
        max_length=255,
        verbose_name="Nombre del Documento",
    )
    documento = models.FileField(
        upload_to="liquidaciones/documentos/",
        verbose_name="Archivo del Documento",
    )

    class Meta:
        verbose_name = "Documento de Liquidación"
        verbose_name_plural = "Documentos de Liquidaciones"
        ordering = ["liquidacion_general", "nombre_documento"]

    def __str__(self):
        return f"{self.nombre_documento} @ {self.liquidacion_general}"


# =============================================================================
# Nuevos modelos del refactor — ver contract/PLAN_REFACTORIZACION.md
# =============================================================================


class LiquidacionProyectista(BaseModel):
    """
    Proyectistas separados de una LiquidacionGeneral.

    Diseño simple — solo FK a LiquidacionGeneral y FK a Proyectista.
    NO agregar campos extra como especialidad, rol, estado, importe, numero_revision.
    """

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_proyectistas",
        verbose_name="Liquidación General",
    )
    proyectista = models.ForeignKey(
        "Proyectista",
        on_delete=models.PROTECT,
        related_name="liquidaciones_proyectista",
        verbose_name="Proyectista",
    )

    class Meta:
        verbose_name = "Proyectista de Liquidación"
        verbose_name_plural = "Proyectistas de Liquidaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_general", "proyectista"],
                name="unique_liquidacion_proyectista",
            ),
        ]

    def __str__(self):
        return f"Proyectista {self.proyectista} @ {self.liquidacion_general}"


class LiquidacionEspecialidadDisponibles(BaseModel):
    """
    Especialidades separadas de una LiquidacionGeneral.

    Diseño simple — solo FK a LiquidacionGeneral y FK a Especialidad.
    NO agregar campos extra como importe, numero_revision.
    """

    history = HistoricalRecords()

    tipo_liquidacion = models.ForeignKey(
        'liquidaciones.TipoLiquidacion',
        on_delete=models.PROTECT,
        related_name='especialidades_disponibles',
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario.",
    )

    especialidad = models.ForeignKey(
        "usuarios.Especialidad",
        on_delete=models.PROTECT,
        related_name="liquidaciones_especialidad",
        verbose_name="Especialidad",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
        help_text="Indica si esta especialidad está disponible para liquidaciones.",
    )

    class Meta:
        verbose_name = "Especialidad de Liquidación"
        verbose_name_plural = "Especialidades de Liquidaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_liquidacion", "especialidad"],
                name="unique_liquidacion_especialidad",
            ),
        ]

    def __str__(self):
        return f"Especialidad {self.especialidad} @ {self.tipo_liquidacion}"

