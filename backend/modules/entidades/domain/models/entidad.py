"""
Entidad — Entidad maestra unificada para instituciones y personas naturales.
El tipo de documento (RUC/DNI) determina la semántica:
- RUC (11 dígitos) => institución
- DNI (8 dígitos) => persona natural
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel

# Opciones de tipo de documento
TIPO_DOCUMENTO_CHOICES = [
    ("RUC", "RUC"),
    ("DNI", "DNI"),
]

# Validador de RUC: exactamente 11 dígitos
ruc_validator = RegexValidator(
    regex=r"^\d{11}$",
    message="El RUC debe contener exactamente 11 dígitos numéricos.",
    code="invalid_ruc",
)

# Validador de DNI: exactamente 8 dígitos
dni_validator = RegexValidator(
    regex=r"^\d{8}$",
    message="El DNI debe contener exactamente 8 dígitos numéricos.",
    code="invalid_dni",
)


class EntidadManager(models.Manager):
    """Manager that filters to only active entities (removed activo field - all entities are now active by default)."""

    def get_queryset(self):
        return super().get_queryset()


class Entidad(BaseModel):
    """
    Entidad maestra unificada.
    Representa tanto instituciones (empresas) como personas naturales.
    El tipo de documento determina la semántica:
    - RUC => institución (empresa, constructora, etc.)
    - DNI => persona natural (proyectista, contacto, etc.)

    Uso de proxy models para acceso semántico:
    - Institucion: entidades con RUC
    - PersonaNatural: entidades con DNI
    """

    history = HistoricalRecords()

    tipo_documento = models.CharField(
        max_length=3,
        choices=TIPO_DOCUMENTO_CHOICES,
        verbose_name="Tipo de Documento",
        help_text="RUC para instituciones, DNI para personas naturales.",
    )
    numero_documento = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        verbose_name="Número de Documento",
        help_text="RUC (11 dígitos) o DNI (8 dígitos).",
    )

    tipo_contribuyente = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tipo de Contribuyente",
        help_text="Todos los tipos de contribuyente posibles (opcional).",
    )
    # Campo unificado para nombre:
    # - Para RUC: razón social de la institución
    # - Para DNI: nombre completo de la persona natural (nombre + apellido)
    razon_social = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Razón Social / Nombre Completo",
        help_text="Para instituciones: razón social. Para personas naturales: nombre completo.",
    )
    nombre_comercial = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nombre Comercial",
    )
    
    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Dirección",
    )

    objects = models.Manager()
    active = EntidadManager()

    class Meta:
        verbose_name = "Entidad"
        verbose_name_plural = "Entidades"
        ordering = ["razon_social"]

    def clean(self):
        if self.tipo_documento == "RUC" and not self.razon_social:
            raise ValidationError(
                {
                    "razon_social": "La razón social es requerida para instituciones (RUC)."
                }
            )
        if self.tipo_documento == "DNI" and not self.razon_social:
            raise ValidationError(
                {
                    "razon_social": "El nombre completo es requerido para personas naturales (DNI)."
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def es_institucion(self):
        """True if this is an institution (RUC)."""
        return self.tipo_documento == "RUC"

    @property
    def es_persona_natural(self):
        """True if this is a natural person (DNI)."""
        return self.tipo_documento == "DNI"

    @property
    def nombre_completo(self):
        """Full name: razon_social for both institutions and natural persons."""
        return self.razon_social or ""

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"


class InstitucionManager(models.Manager):
    """Manager that filters to only institutions (RUC)."""

    def get_queryset(self):
        return super().get_queryset().filter(tipo_documento="RUC")


class Institucion(Entidad):
    """
    Proxy model for institutions (entities with RUC).
    Use this for admin views and queries that specifically need institutions.
    """

    objects = InstitucionManager()
    active = InstitucionManager()

    class Meta:
        proxy = True
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"
        ordering = ["razon_social"]

    def save(self, *args, **kwargs):
        self.tipo_documento = "RUC"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.tipo_documento != "RUC":
            raise ValidationError("Solo se permiten entidades con RUC en Institucion.")


class PersonaNaturalManager(models.Manager):
    """Manager that filters to only natural persons (DNI)."""

    def get_queryset(self):
        return super().get_queryset().filter(tipo_documento="DNI")


class PersonaNatural(Entidad):
    """
    Proxy model for natural persons (entities with DNI).
    Use this for admin views and queries that specifically need natural persons.

    Note: This replaces the old PersonaNatural model. The old model had a separate
    table with just DNI; the new model uses the same Entidad table with tipo_documento='DNI'.
    """

    objects = PersonaNaturalManager()
    active = PersonaNaturalManager()

    class Meta:
        proxy = True
        verbose_name = "Persona Natural"
        verbose_name_plural = "Personas Naturales"
        ordering = ["razon_social"]

    def save(self, *args, **kwargs):
        self.tipo_documento = "DNI"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.tipo_documento != "DNI":
            raise ValidationError(
                "Solo se permiten entidades con DNI en PersonaNatural."
            )


class ContactoEntidad(BaseModel):
    """
    Tabla puente que asocia un Contacto a una Entidad.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación entidad-contacto.

    Reemplaza a ContactoEmpresa para uso general con Entidad.
    """

    history = HistoricalRecords()

    entidad = models.ForeignKey(
        Entidad,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Entidad",
    )
    contacto = models.ForeignKey(
        "Contacto",
        on_delete=models.PROTECT,
        related_name="entidades",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la entidad.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en la entidad.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Entidad - Contacto"
        verbose_name_plural = "Entidades - Contactos"
        ordering = ["-principal", "entidad__razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["entidad", "contacto"],
                name="unique_entidad_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.entidad}"
