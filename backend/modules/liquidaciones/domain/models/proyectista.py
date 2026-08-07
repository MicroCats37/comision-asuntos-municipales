"""
Proyectista — Modelo de profesional responsable de proyectos técnicos.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class Proyectista(BaseModel):
    """
    Profesional responsable de elaborar los proyectos técnicos
    que se incluyen en las liquidaciones.

    Un Proyectista está vinculado a un PerfilIngeniero (source of truth para
    datos CIP/habilitación) y tiene una especialidad requerida para esta
    liquidación específica.

    NOTE: Los campos nombres/apellidos/cip/dni/cap fueron eliminados.
    La identidad del proyectista se obtiene via PerfilIngeniero referenciado.
    """

    history = HistoricalRecords()

    perfil_ingeniero = models.ForeignKey(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="proyectistas",
        verbose_name="Perfil de Ingeniero",
        help_text="Perfil que contiene los datos de identidad del ingeniero.",
    )

    class Meta:
        verbose_name = "Proyectista"
        verbose_name_plural = "Proyectistas"
        ordering = ["perfil_ingeniero__apellido_paterno", "perfil_ingeniero__apellido_materno", "perfil_ingeniero__nombres"]
        constraints = [
            models.UniqueConstraint(
                fields=["perfil_ingeniero"],
                name="unique_proyectista_perfil_ingeniero",
            ),
        ]

    def __str__(self):
        if self.perfil_ingeniero:
            return f"{self.perfil_ingeniero.apellido_paterno} {self.perfil_ingeniero.apellido_materno}, {self.perfil_ingeniero.nombres}"
        return f"Proyectista {self.id}"
