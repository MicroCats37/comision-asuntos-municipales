"""Modelos — re-exportados desde domain/models/."""

from .domain.models import (
    Entidad,
    # Otros modelos
    Alcalde,
    Banco,
    ContactoBanco,
    Contacto,
    GerenteUrbano,
    Municipalidad,
    ContactoMunicipalidad,
    MunicipalidadProvincial,
    MunicipalidadDistrital,
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
    # Constantes
    TIPO_DOCUMENTO_CHOICES,
    ruc_validator,
    dni_validator,
)

# Compatibilidad hacia atrás: re-exportar Entidad como Empresa.
# Permite que código existente importe desde modules.entidades.models import Empresa
# mientras el modelo real ahora es Entidad.
Empresa = Entidad

__all__ = [
    # Modelo principal
    "Entidad",
    # Compatibilidad hacia atrás (se eliminará tras la migración)
    "Empresa",
    # Otros modelos
    "Alcalde",
    "Banco",
    "ContactoBanco",
    "Contacto",
    "GerenteUrbano",
    "Municipalidad",
    "ContactoMunicipalidad",
    "MunicipalidadProvincial",
    "MunicipalidadDistrital",
    "UbigeoDepartamento",
    "UbigeoProvincia",
    "UbigeoDistrito",
    # Constantes
    "TIPO_DOCUMENTO_CHOICES",
    "ruc_validator",
    "dni_validator",
]
