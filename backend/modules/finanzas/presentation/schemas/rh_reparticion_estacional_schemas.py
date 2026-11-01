# -*- coding: utf-8 -*-
"""
Presentation schemas for RH Reparticion Estacional.

HTTP request/response schemas following api-wrapper-presenter-contract.md.
"""

import uuid


from core.types import BaseSchema


class DelegadoMinimalOut(BaseSchema):
    """Minimal delegate info for nested presentation."""

    id: uuid.UUID
    cip: str
    dni: str
    nombre_completo: str


class CapituloMinimalOut(BaseSchema):
    """Minimal chapter info for nested presentation."""

    id: uuid.UUID
    nombre: str


class RHReparticionEstacionalDelegadoOut(BaseSchema):
    """Delegate share composed with its human-readable identity."""

    delegado: DelegadoMinimalOut
    monto: float


class RHReparticionEstacionalCapituloOut(BaseSchema):
    """Chapter share composed with its human-readable identity."""

    capitulo: CapituloMinimalOut
    monto: float


class RHReparticionEstacionalCotizarOut(BaseSchema):
    """
    Output for cotizar (preview) endpoint.
    """

    especialidad_revision_id: uuid.UUID
    especialidad_revision_nombre: str
    periodo: int
    mes_desde: int
    mes_hasta: int
    total_fondo_comun: float
    numero_capitulos: int
    numero_delegados: int
    divisor_total: int
    monto_por_participacion: float
    residual: float
    detalles_delegados: list[RHReparticionEstacionalDelegadoOut]
    detalles_capitulos: list[RHReparticionEstacionalCapituloOut]


class EspecialidadRevisionMinimalOut(BaseSchema):
    """Specialty identity displayed by the RH trimestral list."""

    id: uuid.UUID
    nombre: str


class RHReparticionEstacionalIdentidadOut(BaseSchema):
    """Persistence identity block."""

    id: uuid.UUID
    created_at: str


class RHReparticionEstacionalGeneralOut(BaseSchema):
    """General period and specialty block."""

    especialidad_revision: EspecialidadRevisionMinimalOut
    periodo: int
    mes_desde: int
    mes_hasta: int


class RHReparticionEstacionalDistribucionOut(BaseSchema):
    """Business distribution block for a persisted RH trimestral item."""

    total_fondo_comun: float
    numero_capitulos: int
    numero_delegados: int
    monto_por_participacion: float
    residual: float
    detalles_delegados: list[RHReparticionEstacionalDelegadoOut]
    detalles_capitulos: list[RHReparticionEstacionalCapituloOut]


class RHReparticionEstacionalOut(BaseSchema):
    """Composed output returned for every item of the list endpoint."""

    identidad: RHReparticionEstacionalIdentidadOut
    general: RHReparticionEstacionalGeneralOut
    distribucion: RHReparticionEstacionalDistribucionOut


class RHReparticionEstacionalDeleteOut(BaseSchema):
    """
    Output for DELETE endpoint.

    The human-readable message lives ONLY in the top level of the envelope
    (contract/next-app-architecture-contract.md §11) — it is not duplicated
    inside the payload.
    """

    id: uuid.UUID
