# -*- coding: utf-8 -*-
"""
RHReparticionEstacional result DTOs — domain/results.
"""

from decimal import Decimal
from pydantic import BaseModel


class DelegadoMinimalResult(BaseModel):
    """Minimal delegate info for nested presentation (cotizar/detail)."""

    id: str
    cip: str
    dni: str
    nombre_completo: str


class CapituloMinimalResult(BaseModel):
    """Minimal chapter info for nested presentation (cotizar/detail)."""

    id: str
    nombre: str


class RHReparticionEstacionalDelegadoResult(BaseModel):
    """Detail result for a single delegate share."""

    delegado: DelegadoMinimalResult
    monto: Decimal


class RHReparticionEstacionalCapituloResult(BaseModel):
    """Detail result for a single chapter share."""

    capitulo: CapituloMinimalResult
    monto: Decimal


class RHReparticionEstacionalCotizarResult(BaseModel):
    """
    Result of a cotizacion (preview) for reparticion estacional.

    Includes the full breakdown of the calculation.
    """

    especialidad_revision_id: str
    especialidad_revision_nombre: str
    periodo: int
    mes_desde: int
    mes_hasta: int
    total_fondo_comun: Decimal
    numero_capitulos: int
    numero_delegados: int
    divisor_total: int
    monto_por_participacion: Decimal
    residual: Decimal
    detalles_delegados: list[RHReparticionEstacionalDelegadoResult]
    detalles_capitulos: list[RHReparticionEstacionalCapituloResult]


class RHReparticionEstacionalResult(BaseModel):
    """Complete persisted reparticion returned by the list use case."""

    id: str
    especialidad_revision_id: str
    especialidad_revision_nombre: str
    periodo: int
    mes_desde: int
    mes_hasta: int
    total_fondo_comun: Decimal
    numero_capitulos: int
    numero_delegados: int
    monto_por_participacion: Decimal
    residual: Decimal
    created_at: str
    detalles_delegados: list[RHReparticionEstacionalDelegadoResult]
    detalles_capitulos: list[RHReparticionEstacionalCapituloResult]
