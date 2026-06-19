"""Domain constants — choices and status definitions."""

from django.db import models


class DelegadoStatus(models.TextChoices):
    """Status choices for Delegado."""

    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"
    SUSPENDIDO = "suspendido", "Suspendido"


class TipoDelegado(models.TextChoices):
    """Tipo de Delegado."""

    TITULAR = "titular", "Titular"
    ALTERNO = "alterno", "Alterno"


class EstadoLiquidacion(models.TextChoices):
    """Estado de LiquidacionGeneral."""

    PENDIENTE = "PENDIENTE", "Pendiente"
    APROBADA = "APROBADA", "Aprobada"
    REINGRESADA = "REINGRESADA", "Reingresada"
    RECHAZADA = "RECHAZADA", "Rechazada"


class TipoTramiteEdificaciones(models.TextChoices):
    """Tipo de trámite para liquidaciones de edificaciones."""

    OBRA_NUEVA = "OBRA_NUEVA", "Obra Nueva"
    DEMOLICION = "DEMOLICION", "Demolición"
    AMPLIACION = "AMPLIACION", "Ampliación"
    REMODELACION = "REMODELACION", "Remodelación"
    MODIFICACION_LICENCIA = "MODIFICACION_LICENCIA", "Modificación de Licencia"


class TramiteAccion(models.TextChoices):
    """Acción de trámite asignada según el endpoint usado."""

    PRIMERA_REVISION = "PRIMERA_REVISION", "Primera Revisión"
    REVISION = "REVISION", "Revisión"