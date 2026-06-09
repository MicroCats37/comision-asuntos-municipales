"""
Banco — Entidad maestra de banco.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Banco(BaseModel):
    history = HistoricalRecords()
    """
    Entidad maestra de banco.
    Representa instituciones bancarias con las que opera el sistema CAM.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Código",
        help_text="Código único del banco",
    )
    nombre = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Nombre",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )
    

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class BancoContacto(BaseModel):
    history = HistoricalRecords()

    """
    Tabla puente que asocia un Contacto a un Banco.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación banco-contacto.
    """
    banco = models.ForeignKey(
        Banco,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Banco",
    )
    contacto = models.ForeignKey(
        "Contacto",
        on_delete=models.PROTECT,
        related_name="bancos",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal del banco.",
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Notas sobre el rol de este contacto en el banco.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
    )

    class Meta:
        verbose_name = "Banco - Contacto"
        verbose_name_plural = "Bancos - Contactos"
        ordering = ["-principal", "banco__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["banco", "contacto"],
                name="unique_banco_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.banco}"
