"""Admin package for entidades module — imports all admin submodules."""

from .entidad_admin import EntidadAdmin
from .banco_admin import BancoAdmin
from .municipalidad_admin import (
    MunicipalidadAdmin,
    UbigeoDepartamentoAdmin,
    UbigeoProvinciaAdmin,
    UbigeoDistritoAdmin,
)
from .contacto_admin import ContactoAdmin

__all__ = [
    "EntidadAdmin",
    "BancoAdmin",
    "MunicipalidadAdmin",
    "UbigeoDepartamentoAdmin",
    "UbigeoProvinciaAdmin",
    "UbigeoDistritoAdmin",
    "ContactoAdmin",
]
