"""Validadores para el dominio de liquidaciones."""

from decimal import Decimal
from django.core.exceptions import ValidationError

from utils.ubigeo_schema import is_valid_district_choice

from ..domain.constants import PROYECTO_CON_PLANTAS_TIPICAS_TIPO, MODIFICACION_LICENCIA_TIPO, VARIACION_PROYECTO_APROBADO_TIPO


# Tipos de trámite que permiten valor_base_calculo diferente de valor_proyecto
TIPOS_VALOR_BASE_ALTERNATIVO = {
    PROYECTO_CON_PLANTAS_TIPICAS_TIPO,
    MODIFICACION_LICENCIA_TIPO,
    VARIACION_PROYECTO_APROBADO_TIPO,
}


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


def validate_valor_base_calculo(
    valor_proyecto: Decimal,
    valor_base_calculo: Decimal,
    tipo_tramite: str,
) -> None:
    """
    Valida que valor_base_calculo sea consistente con tipo_tramite.

    Para tipos normales:
        - valor_base_calculo debe ser igual a valor_proyecto

    Para PROYECTO_CON_PLANTAS_TIPICAS, MODIFICACION_LICENCIA, y VARIACION_PROYECTO_APROBADO:
        - valor_base_calculo puede ser diferente (valor alternativo para cálculo)

    Lanza ValidationError si la validación falla.
    """
    if tipo_tramite not in TIPOS_VALOR_BASE_ALTERNATIVO:
        if valor_base_calculo != valor_proyecto:
            raise ValidationError(
                f"Para el tipo de trámite '{tipo_tramite}', valor_base_calculo debe ser igual a valor_proyecto. "
                f"Valor proyecto: {valor_proyecto}, Valor base cálculo: {valor_base_calculo}",
                code="invalid_valor_base_calculo",
            )