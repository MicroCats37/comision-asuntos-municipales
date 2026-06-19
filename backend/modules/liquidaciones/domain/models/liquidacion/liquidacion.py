"""
LiquidacionGeneral — general liquidacion classes and enums.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from ...constants import EstadoLiquidacion


class LiquidacionGeneral(BaseModel):
    """
    Liquidación de pago a proyectistas para un proyecto.
    Representa la instancia operacional de liquidación/revisión de un proyecto.
    """

    history = HistoricalRecords()

    public_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID Público",
        help_text="Identificador público de la liquidación (ej. LIQ-2026-00001).",
    )

    proyecto = models.ForeignKey(
        "Proyecto",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Proyecto",
    )

    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Municipalidad",
        null=True,
        blank=True,
    )
    
    fecha_registro = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de Registro",
    )
    
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="liquidaciones_creadas",
        verbose_name="Usuario Creador",
        null=True,
        blank=True,
    )
    
    igv = models.ForeignKey(
        "finanzas.IGV",
        on_delete=models.PROTECT,
        verbose_name="IGV",
    )

    uit = models.ForeignKey(
        "finanzas.UIT",
        on_delete=models.PROTECT,
        verbose_name="UIT",
    )
    
    estado = models.CharField(
        max_length=20,
        choices=EstadoLiquidacion.choices,
        default="PENDIENTE",
        verbose_name="Estado de la Revisión",
    )
    
    valor_proyecto = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Valor de Obra"
    )
    
    observacion = models.CharField(
        max_length=2000,
        null=True,
        blank=True
    )
    
    liquidaciones_previas = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="revisiones",
        blank=True,
        verbose_name="Liquidaciones Previas",
        help_text="Referencias a liquidaciones anteriores en caso de revisiones sucesivas.",
    )

    class Meta:
        verbose_name = "Liquidación"
        verbose_name_plural = "Liquidaciones"
        ordering = ["proyecto", "-fecha_registro"]

    def __str__(self):
        return f"Liquidación de {self.proyecto}"


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
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la liquidación.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en la liquidación.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
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
    
    liquidacion_maestra = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Liquidación Maestra",
    )
    nombre_documento = models.CharField(
        max_length=255,
        verbose_name="Nombre del Documento",
    )
    documento = models.FileField(
        upload_to="liquidaciones/documentos/",
        verbose_name="Archivo del Documento",
    )

class LiquidacionSnapshot(BaseModel):
    """
    Snapshot temporal de los datos calculados de una liquidación.
    Guarda el resultado generado por el servicio mientras se estabiliza
    la estructura definitiva de campos.
    """

    liquidacion = models.OneToOneField(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="snapshot",
        verbose_name="Liquidación",
    )

    data = models.JSONField(
        default=dict,
        verbose_name="Datos del snapshot",
        help_text="Datos calculados de la liquidación en formato JSON.",
    )

    class Meta:
        verbose_name = "Snapshot de Liquidación"
        verbose_name_plural = "Snapshots de Liquidación"

    def __str__(self):
        return f"Snapshot {self.liquidacion_id} - {self.liquidacion}"
