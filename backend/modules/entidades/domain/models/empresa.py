"""
Empresa — Entidad maestra de empresa con RUC como identificador.
"""

from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


# RUC validator: exactly 11 digits
ruc_validator = RegexValidator(
    regex=r"^\d{11}$",
    message="El RUC debe contener exactamente 11 dígitos numéricos.",
    code="invalid_ruc",
)


class Empresa(BaseModel):
    history = HistoricalRecords()
    """
    Entidad maestra de empresa.
    Representa empresas proveedoras, contratistas o entidades legales relacionadas.
    """
    ruc = models.CharField(
        max_length=11,
        unique=True,
        validators=[ruc_validator],
        db_index=True,
        verbose_name="RUC",
        help_text="11 dígitos numéricos exactamente.",
    )
    razon_social = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Razón Social",
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
    distrito = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Distrito",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )
    

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["razon_social"]

    def __str__(self):
        return f"{self.razon_social} ({self.ruc})"


class EmpresaContacto(BaseModel):
    history = HistoricalRecords()

    """
    Tabla puente que asocia un Contacto a una Empresa.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación empresa-contacto.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Empresa",
    )
    contacto = models.ForeignKey(
        "Contacto",
        on_delete=models.PROTECT,
        related_name="empresas",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la empresa.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en la empresa.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Empresa - Contacto"
        verbose_name_plural = "Empresas - Contactos"
        ordering = ["-principal", "empresa__razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "contacto"],
                name="unique_empresa_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.empresa}"
