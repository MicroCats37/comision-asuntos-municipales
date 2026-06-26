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


class CategoriaDelegado(models.TextChoices):
    """Categoría del Delegado para filter en endpoint de liquidaciones."""

    EDIFICACIONES = "Edificaciones", "Edificaciones"
    HABILITACIONES_URBANAS = "Habilitaciones Urbanas", "Habilitaciones Urbanas"


class EstadoLiquidacion(models.TextChoices):
    """Estado de LiquidacionGeneral."""

    PENDIENTE = "PENDIENTE", "Pendiente"
    APROBADA = "APROBADA", "Aprobada"
    REINGRESADA = "REINGRESADA", "Reingresada"
    RECHAZADA = "RECHAZADA", "Rechazada"


class DictamenRevision(models.TextChoices):
    """Dictamen de revision asociado a un delegado de liquidacion."""

    CONFORME = "CONFORME", "Conforme"
    NO_CONFORME = "NO_CONFORME", "No conforme"
    PENDIENTE = "PENDIENTE", "Pendiente"
    AP_OB = "AP_OB", "AP.OB."


class TipoTramiteEdificaciones(models.TextChoices):
    """Tipo de trámite para liquidaciones de edificaciones."""

    OBRA_NUEVA = "OBRA_NUEVA", "Obra Nueva"
    DEMOLICION = "DEMOLICION", "Demolición"
    AMPLIACION = "AMPLIACION", "Ampliación"
    REMODELACION = "REMODELACION", "Remodelación"
    MODIFICACION_LICENCIA = "MODIFICACION_LICENCIA", "Modificación de Licencia"
    REINTEGRO = "REINTEGRO", "Reintegro"
    PROYECTO_CON_PLANTAS_TIPICAS = "PROYECTO_CON_PLANTAS_TIPICAS", "Proyecto con Plantas Típicas"


# Constants for tramite types that use valor_base_calculo different from valor_proyecto
PROYECTO_CON_PLANTAS_TIPICAS_TIPO = "PROYECTO_CON_PLANTAS_TIPICAS"
    

class TramiteAccion(models.TextChoices):
    """Acción de trámite asignada según el endpoint usado."""

    PRIMERA_REVISION = "PRIMERA_REVISION", "Primera Revisión"
    REVISION = "REVISION", "Revisión"
