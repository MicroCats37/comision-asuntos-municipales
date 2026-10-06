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
    """
    Output for a single delegate share in the reparticion.

    Contains nested ``delegado`` object and flat ``delegado_id`` alias
    for backward compatibility during the transition period.
    """
    # Deprecated — use ``delegado.id`` instead
    delegado_id: uuid.UUID
    # Nested delegate object
    delegado: DelegadoMinimalOut
    monto: float


class RHReparticionEstacionalCapituloOut(BaseSchema):
    """
    Output for a single chapter share in the reparticion.

    Contains nested ``capitulo`` object and flat ``capitulo_id`` alias
    for backward compatibility during the transition period.
    """
    # Deprecated — use ``capitulo.id`` instead
    capitulo_id: uuid.UUID
    # Nested capitulo object
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


class RHReparticionEstacionalListItemOut(BaseSchema):
    """Output for list item (GET list)."""
    id: uuid.UUID
    especialidad_revision_id: uuid.UUID
    especialidad_revision_nombre: str
    periodo: int
    total_fondo_comun: float
    numero_delegados: int
    numero_capitulos: int
    monto_por_participacion: float
    residual: float
    is_deleted: bool
    created_at: str


class RHReparticionEstacionalDetalleOut(BaseSchema):
    """
    Full detail output for GET single reparticion.
    """
    id: uuid.UUID
    especialidad_revision_id: uuid.UUID
    especialidad_revision_nombre: str
    periodo: int
    mes_desde: int
    mes_hasta: int
    total_fondo_comun: float
    numero_capitulos: int
    numero_delegados: int
    monto_por_participacion: float
    residual: float
    is_deleted: bool
    created_at: str
    detalles_delegados: list[RHReparticionEstacionalDelegadoOut]
    detalles_capitulos: list[RHReparticionEstacionalCapituloOut]


class RHReparticionEstacionalDeleteOut(BaseSchema):
    """Output for DELETE endpoint."""
    message: str