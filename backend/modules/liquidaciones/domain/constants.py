"""Domain constants — choices and status definitions."""

from django.db import models


class DelegadoStatus(models.TextChoices):
    """Status choices for Delegado."""

    ACTIVO = "ACTIVO", "Activo"
    INACTIVO = "INACTIVO", "Inactivo"
    SUSPENDIDO = "SUSPENDIDO", "Suspendido"


class TipoDelegado(models.TextChoices):
    """Tipo de Delegado."""

    TITULAR = "TITULAR", "Titular"
    ALTERNO = "ALTERNO", "Alterno"


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
    VARIACION_PROYECTO_APROBADO = "VARIACION_PROYECTO_APROBADO", "Variación Proyecto Aprobado"
    REINTEGRO = "REINTEGRO", "Reintegro"
    PROYECTO_CON_PLANTAS_TIPICAS = "PROYECTO_CON_PLANTAS_TIPICAS", "Proyecto con Plantas Típicas"


# Constants for tramite types that allow valor_base_calculo different from valor_proyecto
PROYECTO_CON_PLANTAS_TIPICAS_TIPO = "PROYECTO_CON_PLANTAS_TIPICAS"
MODIFICACION_LICENCIA_TIPO = "MODIFICACION_LICENCIA"
VARIACION_PROYECTO_APROBADO_TIPO = "VARIACION_PROYECTO_APROBADO"
    

class TipoLiquidacion(models.TextChoices):
    """Tipo de liquidación/formulario de obra."""

    EDIFICACION = "EDIFICACION", "Edificación"
    HABILITACION_URBANA = "HABILITACION_URBANA", "Habilitación Urbana"
    MECANICA_SUELOS = "MECANICA_SUELOS", "Mecánica de Suelos"
    IMPACTO_VIAL = "IMPACTO_VIAL", "Impacto Vial"
    TALUDES = "TALUDES", "Taludes"
    INSPECCION_OBRA = "INSPECCION_OBRA", "Inspección de Obra"


class TramiteAccion(models.TextChoices):
    """Acción de trámite asignada según el endpoint usado."""

    A="A"
    B="B"
    C="C"
    D="D"


# ── Slug → TipoLiquidacion mapping ─────────────────────────────────────────────

# Mapas de slug (usado en URLs y payloads frontend) → valor enum TipoLiquidacion.
# Se usan para normalizar tipo_liquidacion en requests de cotizar/crear.
KIND_SLUG_TO_TIPO_LIQUIDACION: dict[str, str] = {
    "edificacion": TipoLiquidacion.EDIFICACION,
    "habilitacion-urbana": TipoLiquidacion.HABILITACION_URBANA,
    "mecanica-suelos": TipoLiquidacion.MECANICA_SUELOS,
    "impacto-vial": TipoLiquidacion.IMPACTO_VIAL,
    "taludes": TipoLiquidacion.TALUDES,
    "inspeccion-obra": TipoLiquidacion.INSPECCION_OBRA,
}

TIPO_LIQUIDACION_TO_KIND_SLUG: dict[str, str] = {v: k for k, v in KIND_SLUG_TO_TIPO_LIQUIDACION.items()}


def normalizar_tipo_liquidacion(tipo_liquidacion: str) -> str:
    """
    Normaliza un tipo_liquidacion que puede venir como slug (frontend) o como enum (backend).

    - Si ya es un valor enum válido de TipoLiquidacion, lo retorna tal cual.
    - Si es un slug conocido, lo convierte al valor enum correspondiente.
    - Si no es reconocido, retorna el valor original sin modificación.

    Args:
        tipo_liquidacion: Slug (ej. "habilitacion-urbana") o enum (ej. "HABILITACION_URBANA").

    Returns:
        Valor enum normalizado (ej. "HABILITACION_URBANA").
    """
    # Si ya es un valor enum válido, retornarlo
    if tipo_liquidacion in TipoLiquidacion.values:
        return tipo_liquidacion

    # Si es un slug conocido, convertir a enum
    if tipo_liquidacion in KIND_SLUG_TO_TIPO_LIQUIDACION:
        return KIND_SLUG_TO_TIPO_LIQUIDACION[tipo_liquidacion]

    # No reconocido, retornar original (permitirá al caller manejar el error si corresponde)
    return tipo_liquidacion
