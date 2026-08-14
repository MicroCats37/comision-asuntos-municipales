"""Admin package for finanzas module — imports all admin submodules."""

from .impuestos_admin import IGVAdmin, UITAdmin

__all__ = [
    "IGVAdmin",
    "UITAdmin",
]
