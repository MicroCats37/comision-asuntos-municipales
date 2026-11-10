"""
Public API of the shared validity ("vigencia") toolkit.
"""

from core_application.vigencia.constraints import (
    MENSAJE_SOLAPAMIENTO_GLOBAL,
    MENSAJE_SOLAPAMIENTO_OPERACION,
    MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION,
    MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION_ESPECIALIDAD,
    SCOPE_GLOBAL,
    SCOPE_TIPO_LIQUIDACION,
    SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD,
    ExclusionConstraint,
    InclusiveDateRange,
    exclusion_constraint_vigencia,
    mensaje_de_solapamiento,
    vigencia_rango_valido_constraint,
)
from core_application.vigencia.services import (
    cerrar_actual_y_abrir_nuevo,
    cerrar_vigencias_previas,
    hay_solapamiento,
    scope_de,
    validar_periodo_sin_solapamiento,
)

__all__ = [
    "ExclusionConstraint",
    "InclusiveDateRange",
    "MENSAJE_SOLAPAMIENTO_GLOBAL",
    "MENSAJE_SOLAPAMIENTO_OPERACION",
    "MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION",
    "MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION_ESPECIALIDAD",
    "SCOPE_GLOBAL",
    "SCOPE_TIPO_LIQUIDACION",
    "SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD",
    "cerrar_actual_y_abrir_nuevo",
    "cerrar_vigencias_previas",
    "exclusion_constraint_vigencia",
    "hay_solapamiento",
    "mensaje_de_solapamiento",
    "scope_de",
    "validar_periodo_sin_solapamiento",
    "vigencia_rango_valido_constraint",
]
