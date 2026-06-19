"""Modelos de dominio — re-exportados desde domain/models/."""

from .banco import Banco, ContactoBanco
from .contacto import Contacto
from .entidad import (
    Entidad,
    Institucion,
    PersonaNatural,
    ContactoEntidad,
    TIPO_DOCUMENTO_CHOICES,
    ruc_validator,
    dni_validator,
)
from .municipalidad import (
    Alcalde,
    GerenteUrbano,
    Municipalidad,
    ContactoMunicipalidad,
    MunicipalidadProvincial,
    MunicipalidadDistrital,
)
from .ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito

__all__ = [
    "Alcalde",
    "Banco",
    "ContactoBanco",
    "Contacto",
    "Entidad",
    "Institucion",
    "PersonaNatural",
    "ContactoEntidad",
    "GerenteUrbano",
    "Municipalidad",
    "ContactoMunicipalidad",
    "MunicipalidadProvincial",
    "MunicipalidadDistrital",
    "UbigeoDepartamento",
    "UbigeoProvincia",
    "UbigeoDistrito",
    # Constants for reuse
    "TIPO_DOCUMENTO_CHOICES",
    "ruc_validator",
    "dni_validator",
]