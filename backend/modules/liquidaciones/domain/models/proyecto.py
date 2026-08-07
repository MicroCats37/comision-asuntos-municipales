"""
Proyecto — Modelo de proyecto asociado a liquidaciones.
"""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Proyecto(BaseModel):
    """
    Modelo para representar un proyecto asociado a una liquidación.
    Un proyecto puede tener múltiples liquidaciones.

    Un proyecto pertenece a una Entidad (Institución o Persona Natural).
    La entidad determina si es empresarial o persona natural:
    - entidad.tipo_documento='RUC' => ProyectoEmpresarial
    - entidad.tipo_documento='DNI' => ProyectoPersonaNatural

    Los campos entidad_razon_social, entidad_tipo_documento, entidad_numero_documento
    son copias denormalizadas de los campos correspondientes de Entidad.
    Se populan al momento de crear el proyecto (normal o inline) para preservar
    el histórico, ya que la entidad puede ser modificada posteriormente.
    """

    entidad = models.ForeignKey(
        "entidades.Entidad",
        on_delete=models.PROTECT,
        related_name="proyectos",
        verbose_name="Entidad",
        null=True,
        blank=True,
    )
    
    history = HistoricalRecords()

    # Campos denormalizados de la entidad para preservar histórico
    entidad_razon_social = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Razón Social / Nombre de Entidad (snapshot)",
        help_text="Copia de entidad.razon_social al momento de crear el proyecto.",
    )
    entidad_tipo_documento = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        verbose_name="Tipo de Documento de Entidad (snapshot)",
        help_text="Copia de entidad.tipo_documento al momento de crear el proyecto.",
    )
    entidad_numero_documento = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name="Número de Documento de Entidad (snapshot)",
        help_text="Copia de entidad.numero_documento al momento de crear el proyecto.",
    )

    nombre_propietario = models.CharField(
        max_length=255, verbose_name="Nombre del Propietario"
    )
    
    denominacion = models.CharField(
        max_length=255, verbose_name="Denominación del Proyecto"
    )
    
    distrito = models.ForeignKey(
        "entidades.UbigeoDistrito",
        on_delete=models.SET_NULL,
        related_name="proyectos",
        blank=True,
        null=True,
        verbose_name="Distrito del Proyecto",
    )
    
    urbanizacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Urbanización del Proyecto",
    )

    direccion = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="Dirección del Proyecto",
    )

    descripcion = models.TextField(
        blank=True, null=True, verbose_name="Descripción del Proyecto"
    )
    
    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["denominacion"]

    def clean(self):
        if self.entidad and self.entidad.tipo_documento not in ["RUC", "DNI"]:
            raise ValidationError("La entidad debe tener tipo de documento RUC o DNI.")

    def __str__(self):
        return self.denominacion

class ProyectoEmpresarialManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                entidad__isnull=False,
                entidad__tipo_documento="RUC",
            )
        )


class ProyectoPersonaNaturalManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                entidad__isnull=False,
                entidad__tipo_documento="DNI",
            )
        )


class ProyectoEmpresarial(Proyecto):
    """Proxy model: solo proyectos de institución (RUC)."""

    objects = ProyectoEmpresarialManager()

    class Meta:
        proxy = True
        verbose_name = "Proyecto Empresarial"
        verbose_name_plural = "Proyectos Empresariales"


class ProyectoPersonaNatural(Proyecto):
    """Proxy model: solo proyectos de persona natural (DNI)."""

    objects = ProyectoPersonaNaturalManager()

    class Meta:
        proxy = True
        verbose_name = "Proyecto Persona Natural"
        verbose_name_plural = "Proyectos Persona Natural"

