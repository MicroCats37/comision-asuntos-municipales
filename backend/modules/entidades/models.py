"""Modelos — re-exportados desde domain/models/."""

from .domain.models import (
    Entidad,
    Institucion,
    PersonaNatural,
    ContactoEntidad,
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

# Compatibilidad hacia atrás: re-exportar Entidad como Empresa y ContactoEntidad como ContactoEmpresa.
# Permite que código existente importe desde modules.entidades.models import Empresa
# mientras el modelo real ahora es Entidad.
Empresa = Entidad
ContactoEmpresa = ContactoEntidad

__all__ = [
    # Modelo principal
    "Entidad",
    # Modelos proxy
    "Institucion",
    "PersonaNatural",
    # Modelo puente
    "ContactoEntidad",
    # Compatibilidad hacia atrás (se eliminará tras la migración)
    "Empresa",
    "ContactoEmpresa",
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
