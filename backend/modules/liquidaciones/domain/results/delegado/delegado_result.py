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


class EspecialidadRevisionResult(BaseModel):
    """Domain DTO for EspecialidadRevision (nested en delegado/liquidacion)."""
    id: str
    nombre: str


class DelegadoVigenteResult(BaseModel):
    """Domain DTO for a delegado vigente (match municipalidad + especialidad vigente)."""
    id: str
    nombre_completo: str
    cip: str
    especialidad: EspecialidadRevisionResult
    tipo: str


class DelegadosVigentesResult(BaseModel):
    """Domain DTO for GET /delegados/vigentes response."""
    delegados: list[DelegadoVigenteResult]


class TipoLiquidacionMinimalResult(BaseModel):
    """Domain DTO for tipo_liquidacion minimal (codigo + nombre)."""
    codigo: str
    nombre: str


class LiquidacionDelegadoLiquidacionMinimal(BaseModel):
    """Domain DTO for minimal liquidacion summary nested in LiquidacionDelegadoResult."""
    id: str
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional[TipoLiquidacionMinimalResult] = None


class LiquidacionDelegadoDelegadoMinimal(BaseModel):
    """Domain DTO for minimal delegado summary nested in LiquidacionDelegadoResult."""
    id: str
    cip: str
    dni: str
    nombre_completo: str


class LiquidacionDelegadoResult(BaseModel):
    """Domain DTO for a LiquidacionDelegado association."""
    id: str
    liquidacion_id: str
    delegado_id: str
    especialidad_revision: EspecialidadRevisionResult
    liquidacion: Optional[LiquidacionDelegadoLiquidacionMinimal] = None
    delegado: Optional[LiquidacionDelegadoDelegadoMinimal] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None


class LiquidacionDelegadoBatchResult(BaseModel):
    """Domain DTO for the grouped batch result of LiquidacionDelegado."""
    created: list[LiquidacionDelegadoResult]
    updated: list[LiquidacionDelegadoResult]
    deleted: list[str]


class ComprobanteActivoMinimal(BaseModel):
    """Domain DTO for minimal active comprobante (tipo, serie, numero, fecha_emision)."""
    tipo_comprobante: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    fecha_emision: Optional[str] = None


class CandidataResult(BaseModel):
    """Domain DTO for a candidate liquidacion."""
    id: str
    expediente: Optional[str] = None
    numero_revision: int
    sub_total: Optional[float] = None
    total: Optional[float] = None
    municipalidad_nombre: Optional[str] = None
    proyecto_denominacion: Optional[str] = None
    tipo_liquidacion: Optional[TipoLiquidacionMinimalResult] = None
    especialidad_candidata: EspecialidadRevisionResult
    tipo_delegado: str  # TITULAR or ALTERNO
    delegado_operacion_id: str  # ID of the DelegadoOperacion this candidate belongs to
    liquidacion_especifica_numero: Optional[int] = None  # numero from specific model (Edificacion, HU, etc.)
    comprobante_activo: Optional[ComprobanteActivoMinimal] = None  # activo=True comprobante


class DelegadoCandidatasResult(BaseModel):
    """Domain DTO for GET /delegados-candidatas."""
    delegado: LiquidacionDelegadoDelegadoMinimal
    candidatas: list[CandidataResult]
    total: int


class DelegadoOperacionVigenteResult(BaseModel):
    """Domain DTO for a single DelegadoOperacion vigencia entry."""
    id: str
    municipalidad_id: str
    municipalidad_nombre: str
    tipo_liquidacion_id: Optional[str] = None
    tipo_liquidacion_codigo: Optional[str] = None
    tipo_liquidacion_nombre: Optional[str] = None
    especialidad_id: str
    especialidad_nombre: str
    tipo: str  # TITULAR or ALTERNO
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None


class DelegadoOperatividadesVigentesResult(BaseModel):
    """Domain DTO for GET /delegados/operatividades-vigentes response."""
    delegado_id: str
    cip: str
    nombre_completo: str
    operatividades: list[DelegadoOperacionVigenteResult]
