"""
Contacto — Entidad de contacto reutilizable entre Entidad, Municipalidad y Banco.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Contacto(BaseModel):
    
    history = HistoricalRecords()
    
    """
    Entidad de contacto reutilizable.
    Puede asociarse a Empresa, Municipalidad, Banco u otras entidades mediante
    tablas puente (ContactoEmpresa, ContactoMunicipalidad, ContactoBanco).
    No es un GenericForeignKey — cada relación tiene su propia tabla puente
    con FK explícitas para mantener integridad referencial real.
    """
    
    nombres = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nombres",
    )
    apellidos = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Apellidos",
    )
    dni = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="DNI",
    )
    cargo = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Cargo",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Teléfono",
    )
    celular = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Celular",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Correo electrónico",
    )
    
    direccion = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="Dirección",
    )

    class Meta:
        verbose_name = "Contacto"
        verbose_name_plural = "Contactos"
        ordering = ["nombres", "apellidos"]

    def __str__(self):
        partes = []
        if self.nombres:
            partes.append(self.nombres)
        if self.apellidos:
            partes.append(self.apellidos)
        if partes:
            return " ".join(partes)
        if self.email:
            return self.email
        if self.telefono:
            return self.telefono
        if self.celular:
            return self.celular
        return f"Contacto sin datos"
