"""Domain constants — choices and status definitions."""

from django.db import models


class DelegadoStatus(models.TextChoices):
    """Status choices for Delegado."""

    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"
    SUSPENDIDO = "suspendido", "Suspendido"