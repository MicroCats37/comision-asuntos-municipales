"""Admin package for finanzas module — imports all admin submodules."""

from .impuestos_admin import IGVAdmin, UITAdmin
from .descuento_inspector_admin import (
    EscalaDescuentoInspectorAdmin,
    RangoDescuentoInspectorAdmin,
    ReciboHonorarioInspectorAdmin,
)

__all__ = [
    "IGVAdmin",
    "UITAdmin",
    "EscalaDescuentoInspectorAdmin",
    "RangoDescuentoInspectorAdmin",
    "ReciboHonorarioInspectorAdmin",
]
