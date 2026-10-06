# -*- coding: utf-8 -*-
"""
RHReparticionEstacional result DTOs — domain/results.
"""
from decimal import Decimal
from typing import Optional

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
    delegado_id: str
    delegado: DelegadoMinimalResult
    monto: Decimal


class RHReparticionEstacionalCapituloResult(BaseModel):
    """Detail result for a single chapter share."""
    capitulo_id: str
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


class RHReparticionEstacionalListItemResult(BaseModel):
    """Minimal result for list view of a reparticion estacional."""
    id: str
    especialidad_revision_id: str
    especialidad_revision_nombre: str
    periodo: int
    total_fondo_comun: Decimal
    numero_delegados: int
    numero_capitulos: int
    monto_por_participacion: Decimal
    residual: Decimal
    is_deleted: bool
    created_at: str


class RHReparticionEstacionalDetalleResult(BaseModel):
    """
    Full detail result for a single reparticion estacional.
    """
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
    is_deleted: bool
    created_at: str
    detalles_delegados: list[RHReparticionEstacionalDelegadoResult]
    detalles_capitulos: list[RHReparticionEstacionalCapituloResult]