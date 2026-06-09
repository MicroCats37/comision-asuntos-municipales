"""Domain models — re-exported from domain/models/."""

from .empresa import Empresa, EmpresaContacto
from .municipalidad import Municipalidad, MunicipalidadContacto
from .banco import Banco, BancoContacto
from .contacto import Contacto

__all__ = [
    "Empresa",
    "Municipalidad",
    "Banco",
    "Contacto",
    "EmpresaContacto",
    "MunicipalidadContacto",
    "BancoContacto",
]
