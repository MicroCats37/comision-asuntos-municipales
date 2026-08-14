"""Admin package for usuarios module — imports all admin submodules."""

from .usuario_admin import UsuarioAdmin
from .perfil_admin import PerfilIngenieroAdmin
from .catalogo_admin import (
    CapituloAdmin,
    EspecialidadIngenieroAdmin,
    EspecialidadRevisionAdmin,
    IngenieroHabilitacionAdmin,
)

__all__ = [
    "UsuarioAdmin",
    "PerfilIngenieroAdmin",
    "CapituloAdmin",
    "EspecialidadIngenieroAdmin",
    "EspecialidadRevisionAdmin",
    "IngenieroHabilitacionAdmin",
]
