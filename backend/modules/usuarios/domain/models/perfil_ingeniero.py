"""
PerfilIngeniero — Perfil profesional del ingeniero asociado a un usuario.
Relación OneToOne con Usuario (un usuario tiene un único perfil ingeniero).
"""

from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Capitulo(BaseModel):
    history = HistoricalRecords()
    """
    Capítulo profesional al que puede pertenecer un ingeniero.
    Un ingeniero puede pertenecer a múltiples capítulos (ManyToMany).
    """
    registro_id = models.CharField(
        max_length=4, unique=True, verbose_name="ID de Registro del Capítulo"
    )

    abreviacion = models.CharField(
        max_length=100, unique=True, verbose_name="Abreviación del Capítulo"
    )

    nombre = models.CharField(
        max_length=100, unique=True, verbose_name="Nombre del Capítulo"
    )

    grupo_envio_intitucional = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Grupo de Envío Institucional",
    )

    class Meta:
        verbose_name = "Capítulo"
        verbose_name_plural = "Capítulos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Especialidad(BaseModel):
    history = HistoricalRecords()
    """
    Especialidad profesional del ingeniero.
    Un ingeniero puede tener múltiples especialidades (ManyToMany).
    """
    codigo = models.CharField(
        max_length=4, unique=True, verbose_name="Código de Especialidad"
    )

    nombre = models.CharField(
        max_length=100, unique=True, verbose_name="Nombre de Especialidad"
    )

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class PerfilIngeniero(BaseModel):
    history = HistoricalRecords()
    """
    Perfil profesional del ingeniero.
    Un usuario tiene exactamente un PerfilIngeniero (OneToOne).
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_ingeniero",
        verbose_name="Usuario",
        null=True,
        blank=True,
    )
    
    nombres = models.CharField(
        max_length=200,
        verbose_name="Nombres",
    )
    apellido_paterno = models.CharField(
        max_length=100,
        verbose_name="Apellido Paterno",
    )
    apellido_materno = models.CharField(
        max_length=100,
        verbose_name="Apellido Materno",
    )
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Nacimiento",
    )
    genero = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Género",
    )
    cip = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="CIP",
        help_text="Número de CIP del ingeniero.",
    )
    dni = models.CharField(
        max_length=8,
        unique=True,
        verbose_name="DNI",
        help_text="DNI del ingeniero (8 dígitos).",
    )
    correo_personal = models.EmailField(
        max_length=255, blank=True, null=True, verbose_name="Correo Personal"
    )

    correo_institucional = models.EmailField(
        max_length=255, blank=True, null=True, verbose_name="Correo Institucional"
    )

    direccion = models.CharField(
        max_length=512, blank=True, null=True, verbose_name="Dirección"
    )

    ubigeo = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="Ubigeo",
        help_text="Código de ubigeo del lugar de residencia.",
    )

    especialidad= models.ForeignKey(
        "Especialidad",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ingenieros",
        verbose_name="Especialidad Profesional",
    )

    capitulo = models.ForeignKey(
        "Capitulo",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ingenieros",
        verbose_name="Capítulo Profesional",
    )

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno}"

    class Meta:
        verbose_name = "Perfil Ingeniero"
        verbose_name_plural = "Perfiles Ingenieros"
        ordering = ["apellido_paterno", "apellido_materno", "nombres"]

    def __str__(self):
        return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno} (CIP: {self.cip})"


class IngenieroHabilitacion(BaseModel):
    history = HistoricalRecords()
    """
    Modelo para almacenar información de habilitacion historica
    """
    perfil_ingeniero = models.ForeignKey(
        "PerfilIngeniero",
        on_delete=models.CASCADE,
        related_name="habilitacion",
        verbose_name="Perfil de Ingeniero",
    )

    ultimo_periodo_pagado_cip = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Último Período Pagado CIP",
        help_text="Último período pagado según CIP.",
    )
    
    condicion_cip = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Condición CIP",
        help_text="Condición del ingeniero según CIP (ej. '1' = habilitado).",
    )
    
