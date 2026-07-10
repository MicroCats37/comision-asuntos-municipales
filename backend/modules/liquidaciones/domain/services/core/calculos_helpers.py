"""
Cálculos Helpers — funciones puras de cálculo para especialidades M2 y visitas.

Contiene helpers stateless para:
- Cálculo por metro cuadrado (M2) para habilitación urbana, mecánica de suelos,
  impacto vial y taludes.
- Cálculo por categoría de visitas para inspección de obra.

NO usa ORM ni transaction.atomic — son funciones matemáticas puras.
"""

from decimal import Decimal
from typing import Optional


def _calcular_monto_m2(
    area_solicitada: Decimal,
    costo_m2: Decimal,
    area_m2: Decimal,
    derecho_minimo: Decimal,
    derecho_maximo: Optional[Decimal],
) -> tuple[Decimal, Decimal]:
    """
    Calcula el monto por metro cuadrado con aplicación de área base y límites.

    El área de cálculo es max(area_solicitada, area_m2).
    El derecho se calcula como area_calculo * costo_m2, luego clampado
    entre derecho_minimo y derecho_maximo.

    Args:
        area_solicitada: Área total solicitada en m2.
        costo_m2: Costo por metro cuadrado en soles.
        area_m2: Área base en m2 (se usa max(area_solicitada, area_m2)).
        derecho_minimo: Monto mínimo absoluto del derecho en soles.
        derecho_maximo: Monto máximo absoluto del derecho en soles (None = sin tope).

    Returns:
        Tuple of (area_base_calculo, derecho):
        - area_base_calculo: Área usada para el cálculo (max de las dos).
        - derecho: Monto del derecho calculado y clamped.
    """
    # Convertir todos los inputs numéricos a Decimal para evitar float*Decimal
    area_solicitada_d = Decimal(str(area_solicitada))
    area_m2_d = Decimal(str(area_m2))
    derecho_minimo_d = Decimal(str(derecho_minimo))
    derecho_maximo_d = Decimal(str(derecho_maximo)) if derecho_maximo is not None else None

    # Monto base = área de cálculo * costo por m2
    area_calculo = max(area_solicitada_d, area_m2_d)
    monto_base = area_calculo * costo_m2

    # Aplicar derecho mínimo
    derecho = monto_base
    if derecho < derecho_minimo_d:
        derecho = derecho_minimo_d

    # Aplicar derecho máximo si está configurado
    if derecho_maximo_d is not None and derecho > derecho_maximo_d:
        derecho = derecho_maximo_d

    return area_calculo, derecho


def _calcular_monto_visitas(
    cantidad_visitas: int,
    costo_visita: Decimal,
    visitas_minimas: int,
) -> tuple[int, Decimal]:
    """
    Calcula el monto por categoría de visitas con aplicación de mínimo de visitas.

    La cantidad base de visitas es max(cantidad_visitas, visitas_minimas).
    El derecho se calcula como visitas_base_calculo * costo_visita.

    Args:
        cantidad_visitas: Número de visitas de inspección solicitadas.
        costo_visita: Costo por cada visita en soles.
        visitas_minimas: Número mínimo de visitas (se usa max(cantidad_visitas, visitas_minimas)).

    Returns:
        Tuple of (visitas_base_calculo, derecho):
        - visitas_base_calculo: Cantidad de visitas usadas para el cálculo.
        - derecho: Monto del derecho calculado.
    """
    # Visitas base de cálculo: max entre solicitadas y mínimas
    visitas_base = max(cantidad_visitas, visitas_minimas)

    # Derecho = visitas base * costo por visita
    derecho = Decimal(visitas_base) * costo_visita

    return visitas_base, derecho


def _aplicar_derecho_minimo(monto: Decimal, derecho_minimo: Decimal) -> Decimal:
    """
    Aplica el floor de derecho mínimo a un monto.

    Args:
        monto: Monto calculado antes de aplicar mínimo.
        derecho_minimo: Monto mínimo absoluto.

    Returns:
        Decimal con el monto elevado al mínimo si era menor.
    """
    if monto < derecho_minimo:
        return derecho_minimo
    return monto


def _aplicar_derecho_maximo(monto: Decimal, derecho_maximo: Optional[Decimal]) -> Decimal:
    """
    Aplica el ceiling de derecho máximo a un monto.

    Args:
        monto: Monto calculado antes de aplicar máximo.
        derecho_maximo: Monto máximo absoluto (None = sin tope).

    Returns:
        Decimal con el monto reducido al máximo si era mayor.
    """
    if derecho_maximo is not None and monto > derecho_maximo:
        return derecho_maximo
    return monto
