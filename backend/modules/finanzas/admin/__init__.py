"""Admin package for finanzas module — imports all admin submodules."""

from .impuestos_admin import IGVAdmin, UITAdmin
from .descuento_inspector_admin import (
    EscalaDescuentoInspectorAdmin,
    RangoDescuentoInspectorAdmin,
    ReciboHonorarioInspectorAdmin,
)
from .tasa_delegado_admin import TasaDelegadoAdmin

__all__ = [
    "IGVAdmin",
    "UITAdmin",
    "EscalaDescuentoInspectorAdmin",
    "RangoDescuentoInspectorAdmin",
    "ReciboHonorarioInspectorAdmin",
    "TasaDelegadoAdmin",
]
