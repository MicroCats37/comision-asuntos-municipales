"""
Delegado Schemas — API output contracts.

Inherit from BaseSchema. Used for API responses.
"""
from core.types import BaseSchema
from typing import Optional
import uuid


class EspecialidadOut(BaseSchema):
    """Output schema for especialidad."""
    id: uuid.UUID
    codigo: str
    nombre: str


class CapituloOut(BaseSchema):
    """Output schema for capitulo."""
    id: uuid.UUID
    registro_id: str
    abreviacion: str
    nombre: str


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
    especialidad: Optional[EspecialidadOut] = None
    capitulo: Optional[CapituloOut] = None


class MunicipalidadBasicOut(BaseSchema):
    """Output schema for municipalidad basica."""
    id: uuid.UUID
    codigo: str
    nombre: str


class DelegadoOut(BaseSchema):
    """Output schema for a Delegado (list item) con municipalidades y estado."""
    id: uuid.UUID
    perfil_ingeniero: PerfilIngenieroOut
    municipalidades: list["MunicipalidadesAsignadasOut"] = []
    estado: str  # vigente | sin_vigencia | sin_asignaciones


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
    municipalidad: MunicipalidadBasicOut
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
