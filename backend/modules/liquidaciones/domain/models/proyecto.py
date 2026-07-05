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

    public_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID Público",
        help_text="Identificador público del proyecto (ej. PROY-2026-00001).",
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
    
    direccion = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="Dirección del Proyecto",
    )

    descripcion = models.TextField(
        blank=True, null=True, verbose_name="Descripción del Proyecto"
    )
    
    observaciones = models.TextField(
        max_length=2000,
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["denominacion"]

    def clean(self):
        if self.entidad and self.entidad.tipo_documento not in ["RUC", "DNI"]:
            raise ValidationError("La entidad debe tener tipo de documento RUC o DNI.")

    @property
    def es_empresarial(self):
        """Verdadero si el proyecto pertenece a una institución (RUC)."""
        return bool(self.entidad and self.entidad.tipo_documento == "RUC")

    @property
    def es_persona_natural(self):
        """Verdadero si el proyecto pertenece a una persona natural (DNI)."""
        return bool(self.entidad and self.entidad.tipo_documento == "DNI")

    # Propiedades de compatibilidad hacia atrás
    @property
    def empresa(self):
        """Compatibilidad hacia atrás: retorna self.entidad si es una institución, sino None."""
        if self.entidad and self.entidad.es_institucion:
            return self.entidad
        return None

    @property
    def persona_natural(self):
        """Compatibilidad hacia atrás: retorna self.entidad si es persona natural, sino None."""
        if self.entidad and self.entidad.es_persona_natural:
            return self.entidad
        return None

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


class ContactoProyecto(BaseModel):
    """
    Tabla puente que asocia un Contacto a un Proyecto.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación proyecto-contacto.
    """

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Proyecto",
    )
    contacto = models.ForeignKey(
        "entidades.Contacto",
        on_delete=models.PROTECT,
        related_name="proyectos",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal del proyecto.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en el proyecto.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Proyecto - Contacto"
        verbose_name_plural = "Proyectos - Contactos"
        ordering = ["-principal", "proyecto__denominacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["proyecto", "contacto"],
                name="unique_proyecto_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.proyecto}"
