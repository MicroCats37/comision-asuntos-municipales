"""
Municipalidad — Entidad maestra de municipalidad.
"""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from utils.ubigeo_schema import get_provincia_choices, get_distrito_flat_choices


class Municipalidad(BaseModel):
    history = HistoricalRecords()
    """
    Entidad maestra de municipalidad.
    Representa gobiernos locales con los que interactúa el sistema CAM.

    Una municipalidad es provincial O distrital — nunca ambas.
    provincia no-null → MunicipalidadProvincial.
    distrito no-null → MunicipalidadDistrital.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Código",
        help_text="Código único de la municipalidad.",
    )
    nombre = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Nombre",
    )

    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Dirección",
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
    )
    provincia = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        db_index=True,
        choices=get_provincia_choices(),
        verbose_name="Provincia",
        help_text="Nombre de la provincia. Solo si es municipalidad provincial.",
    )
    distrito = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        db_index=True,
        choices=get_distrito_flat_choices(),
        verbose_name="Distrito",
        help_text="Nombre del distrito. Solo si es municipalidad distrital.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Municipalidad"
        verbose_name_plural = "Municipalidades"
        ordering = ["nombre"]

    def clean(self):
        if self.provincia and self.distrito:
            raise ValidationError(
                "Una municipalidad no puede ser provincial y distrital a la vez. "
                "Complete provincia O distrito, no ambos."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def es_provincial(self):
        return bool(self.provincia and not self.distrito)

    @property
    def es_distrital(self):
        return bool(self.distrito and not self.provincia)

    def __str__(self):
        tipo = "Provincial" if self.es_provincial else "Distrital" if self.es_distrital else ""
        return f"{self.nombre} ({tipo})" if tipo else self.nombre


class MunicipalidadProvincial(Municipalidad):
    """Proxy model: solo municipalidades provinciales (provincia seteado, distrito null)."""

    class Meta:
        proxy = True
        verbose_name = "Municipalidad Provincial"
        verbose_name_plural = "Municipalidades Provinciales"


class MunicipalidadDistrital(Municipalidad):
    """Proxy model: solo municipalidades distritales (distrito seteado, provincia null)."""

    class Meta:
        proxy = True
        verbose_name = "Municipalidad Distrital"
        verbose_name_plural = "Municipalidades Distritales"


class MunicipalidadContacto(BaseModel):
    history = HistoricalRecords()

    """
    Tabla puente que asocia un Contacto a una Municipalidad.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación municipalidad-contacto.
    """
    municipalidad = models.ForeignKey(
        Municipalidad,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Municipalidad",
    )
    contacto = models.ForeignKey(
        "Contacto",
        on_delete=models.PROTECT,
        related_name="municipalidades",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la municipalidad.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en la municipalidad.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Municipalidad - Contacto"
        verbose_name_plural = "Municipalidades - Contactos"
        ordering = ["-principal", "municipalidad__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipalidad", "contacto"],
                name="unique_municipalidad_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.municipalidad}"


class Alcalde(BaseModel):
    history = HistoricalRecords()

    """
    Alcalde de una municipalidad.
    Permite almacenar información histórica de alcaldes anteriores.
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del Alcalde",
    )
    municipalidad = models.ForeignKey(
        Municipalidad,
        on_delete=models.CASCADE,
        related_name="alcaldes",
        verbose_name="Municipalidad",
    )
    periodo_inicio = models.DateField(
        blank=True,
        null=True,
        verbose_name="Inicio del Período",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fin del Período",
    )

    class Meta:
        verbose_name = "Alcalde"
        verbose_name_plural = "Alcaldes"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"{self.nombre} ({self.municipalidad})"
    
class GerenteUrbano(BaseModel):
    history = HistoricalRecords()

    """
    Gerente Urbano de una municipalidad.
    Permite almacenar información histórica de gerentes urbanos anteriores.
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del Gerente Urbano",
    )
    municipalidad = models.ForeignKey(
        Municipalidad,
        on_delete=models.CASCADE,
        related_name="gerentes_urbanos",
        verbose_name="Municipalidad",
    )
    periodo_inicio = models.DateField(
        blank=True,
        null=True,
        verbose_name="Inicio del Período",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fin del Período",
    )

    class Meta:
        verbose_name = "Gerente Urbano"
        verbose_name_plural = "Gerentes Urbanos"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"{self.nombre} ({self.municipalidad})"