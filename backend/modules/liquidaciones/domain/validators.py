"""Validators for liquidaciones domain."""

from django.core.exceptions import ValidationError

from utils.ubigeo_schema import is_valid_district_choice


def validate_distrito(value: str) -> None:
    """
    Validate that the given value is a valid district choice.

    The value must match the full hierarchical format:
    "DEPARTAMENTO - PROVINCIA - DISTRITO" (e.g. "LIMA - LIMA - MIRAFLORES").

    Raises ValidationError if invalid.
    """
    if not is_valid_district_choice(value):
        raise ValidationError(
            f"'{value}' no es un distrito válido según el ubigeo nacional.",
            code="invalid_distrito",
        )