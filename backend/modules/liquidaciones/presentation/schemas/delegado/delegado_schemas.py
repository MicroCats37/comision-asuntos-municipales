"""
Delegado Schemas — API output contracts.

Inherit from BaseSchema. Used for API responses.
"""
from core.types import BaseSchema
from typing import Optional
import uuid


class PerfilIngenieroOut(BaseSchema):
    """Output schema for ingeniero profile info."""
    id: uuid.UUID
    cip: str
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    nombre_completo: str
    correo_personal: Optional[str] = None
    correo_institucional: Optional[str] = None


class DelegadoOut(BaseSchema):
    """Output schema for a basic Delegado (list item)."""
    id: uuid.UUID
    perfil_ingeniero: PerfilIngenieroOut


class DelegadoListOut(BaseSchema):
    """Output schema for paginated Delegado list."""
    items: list[DelegadoOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class MunicipalidadesAsignadasOut(BaseSchema):
    """Output schema for a municipalidad assignment with vigencia status."""
    id: uuid.UUID
    municipalidad_id: uuid.UUID
    municipalidad_nombre: str
    tipo: str
    categoria: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fin: Optional[str] = None
    es_vigente: bool


class DelegadoMunicipalidadesOut(BaseSchema):
    """Output schema for a delegado's municipalidad assignments."""
    delegado_id: uuid.UUID
    perfil_ingeniero: PerfilIngenieroOut
    municipalidades: list[MunicipalidadesAsignadasOut]


class DelegadoForMunicipalidadOut(BaseSchema):
    """Output schema for a delegado in a municipalidad context."""
    id: uuid.UUID
    perfil_ingeniero: PerfilIngenieroOut
    tipo: str
    categoria: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fin: Optional[str] = None
    es_vigente: bool


class DelegadosPorMunicipalidadOut(BaseSchema):
    """Output schema for paginated list of delegados for a municipalidad."""
    items: list[DelegadoForMunicipalidadOut]
    total: int
    page: int
    page_size: int
    total_pages: int
