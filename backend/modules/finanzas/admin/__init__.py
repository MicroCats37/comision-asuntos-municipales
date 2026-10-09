"""Admin package for finanzas module — imports all admin submodules."""

from .impuestos_admin import IGVAdmin, UITAdmin
from .descuento_inspector_admin import (
    EscalaDescuentoInspectorAdmin,
    RangoDescuentoInspectorAdmin,
    ReciboHonorarioInspectorAdmin,
)
from .tasa_delegado_admin import TasaDelegadoAdmin
from .rh_admin import (
    DetalleHonorarioDelegadoInline,
    DetalleHonorarioInspectorInline,
    ReciboHonorarioDelegadoAdmin,
    ReciboHonorarioDelegadoMensualAdmin,
    ReciboHonorarioInspectorMensualAdmin,
    RegistroPagoInspectorAdmin,
    RHReparticionEstacionalAdmin,
    RHReparticionEstacionalDelegadoInline,
    RHReparticionEstacionalCapituloInline,
)

__all__ = [
    "IGVAdmin",
    "UITAdmin",
    "EscalaDescuentoInspectorAdmin",
    "RangoDescuentoInspectorAdmin",
    "ReciboHonorarioInspectorAdmin",
    "TasaDelegadoAdmin",
    "DetalleHonorarioDelegadoInline",
    "DetalleHonorarioInspectorInline",
    "ReciboHonorarioDelegadoAdmin",
    "ReciboHonorarioDelegadoMensualAdmin",
    "ReciboHonorarioInspectorMensualAdmin",
    "RegistroPagoInspectorAdmin",
    "RHReparticionEstacionalAdmin",
    "RHReparticionEstacionalDelegadoInline",
    "RHReparticionEstacionalCapituloInline",
]
