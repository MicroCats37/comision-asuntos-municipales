from pydantic import BaseModel
from typing import Optional


class EntidadResult(BaseModel):
    razon_social: str
    tipo_documento: str
    numero_documento: str


class DepartamentoResult(BaseModel):
    id: str
    nombre: str


class ProvinciaResult(BaseModel):
    id: str
    nombre: str
    departamento: Optional[DepartamentoResult] = None


class DistritoResult(BaseModel):
    id: str
    nombre: str
    ubigeo: Optional[str] = None
    provincia: Optional[ProvinciaResult] = None
    departamento: Optional[DepartamentoResult] = None


class ProyectoResult(BaseModel):
    id: str
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito: Optional[DistritoResult] = None
    # Denormalized entity fields (mirrors ORM proyecto.entidad_*)
    entidad_tipo_documento: Optional[str] = None
    entidad_numero_documento: Optional[str] = None
    entidad_razon_social: Optional[str] = None
    entidad: Optional[EntidadResult] = None


class UsuarioCreadorResult(BaseModel):
    id: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    dni: Optional[str] = None
    username: Optional[str] = None


class MunicipalidadResult(BaseModel):
    id: str
    codigo: str
    nombre: str


class IgvResult(BaseModel):
    id: str
    valor: float
    periodo_inicio: Optional[str] = None


class UitResult(BaseModel):
    id: str
    valor: float
    periodo_inicio: Optional[str] = None


class LiquidacionPreviaResult(BaseModel):
    """Resumen de una liquidación previa del mismo proyecto."""
    id: str
    numero_revision: int
    expediente: Optional[str] = None


class ContactoResult(BaseModel):
    id: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None


class TipoLiquidacionResult(BaseModel):
    """Tipo de liquidacion en el resultado domain — solo codigo y nombre."""
    codigo: str
    nombre: str


class LiquidacionDelegadoEnGeneralResult(BaseModel):
    """
    Minimal domain DTO for a LiquidacionDelegado nested inside LiquidacionGeneralResult.
    Carries the same fields as LiquidacionDelegadoOut minus the nested liquidacion
    (to avoid circular nesting inside liquidacion_general).
    """
    id: str
    liquidacion_id: str
    delegado_id: str
    especialidad_revision_id: str
    especialidad_revision_nombre: str
    delegado_cip: str
    delegado_dni: str
    delegado_nombre_completo: str
    periodo: Optional[str] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class LiquidacionGeneralResult(BaseModel):
    id: str
    municipalidad: MunicipalidadResult
    usuario_creador: UsuarioCreadorResult
    fecha_registro: str  # NEW
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    numero_revision: int
    sub_total: float
    total: float
    retencion: bool = False
    igv: Optional[IgvResult] = None  # NEW
    uit: Optional[UitResult] = None  # NEW
    proyecto: ProyectoResult
    contacto: Optional[ContactoResult] = None
    tipo_liquidacion: Optional[TipoLiquidacionResult] = None
    revisiones_previas: list[LiquidacionPreviaResult] = []
    delegados: list[LiquidacionDelegadoEnGeneralResult] = []
