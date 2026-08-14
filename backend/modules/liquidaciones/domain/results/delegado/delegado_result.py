"""
Delegado Domain Results — Internal DTOs for Orchestrator → Presenter.

NO ORM imports. Pure Pydantic BaseModel domain objects.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date


class EspecialidadResult(BaseModel):
    """Domain DTO for especialidad."""
    id: str
    codigo: str
    nombre: str


class CapituloResult(BaseModel):
    """Domain DTO for capitulo."""
    id: str
    registro_id: str
    abreviacion: str
    nombre: str


class PerfilIngenieroResult(BaseModel):
    """Domain DTO for ingeniero profile info (delegado list item)."""
    id: str
    cip: str
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    nombre_completo: str
    correo_personal: Optional[str] = None
    correo_institucional: Optional[str] = None
    especialidad: Optional[EspecialidadResult] = None
    capitulo: Optional[CapituloResult] = None


class DelegadoResult(BaseModel):
    """Domain DTO for a Delegado (list item) con municipalidades y estado."""
    id: str
    perfil_ingeniero: PerfilIngenieroResult
    municipalidades: list["MunicipalidadesAsignadasResult"] = []
    estado: str = "sin_asignaciones"  # vigente | sin_vigencia | sin_asignaciones


class DelegadoListResult(BaseModel):
    """Domain DTO for paginated Delegado list."""
    items: list[DelegadoResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class MunicipalidadBasicResult(BaseModel):
    """Domain DTO for municipalidad basica."""
    id: str
    codigo: str
    nombre: str


class MunicipalidadesAsignadasResult(BaseModel):
    """Domain DTO for a municipalidad assignment with vigencia status."""
    id: str
    municipalidad: MunicipalidadBasicResult
    tipo: str
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None
    es_vigente: bool


class DelegadoMunicipalidadesResult(BaseModel):
    """Domain DTO for a delegado's municipalidad assignments."""
    delegado_id: str
    perfil_ingeniero: PerfilIngenieroResult
    municipalidades: list[MunicipalidadesAsignadasResult]


class DelegadoForMunicipalidadResult(BaseModel):
    """Domain DTO for a delegado in a municipalidad context (municipalidad/id endpoint)."""
    id: str
    perfil_ingeniero: PerfilIngenieroResult
    tipo: str
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None
    es_vigente: bool


class DelegadosPorMunicipalidadResult(BaseModel):
    """Domain DTO for paginated list of delegados for a municipalidad."""
    items: list[DelegadoForMunicipalidadResult]
    total: int
    page: int
    page_size: int
    total_pages: int
