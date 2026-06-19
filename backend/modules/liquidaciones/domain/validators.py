"""Validadores para el dominio de liquidaciones."""

from django.core.exceptions import ValidationError

from utils.ubigeo_schema import is_valid_district_choice


def validate_distrito(value: str) -> None:
    """
    Valida que el valor proporcionado sea una elección de distrito válida.

    El valor debe coincidir con el formato jerárquico completo:
    "DEPARTAMENTO - PROVINCIA - DISTRITO" (ej. "LIMA - LIMA - MIRAFLORES").

    Lanza ValidationError si es inválido.
    """
    if not is_valid_district_choice(value):
        raise ValidationError(
            f"'{value}' no es un distrito válido según el ubigeo nacional.",
            code="invalid_distrito",
        )