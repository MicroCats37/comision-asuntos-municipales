"""
Domain schemas — DTOs internos para servicios de Proyecto.
"""
import uuid
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class EntidadSimpleData(BaseModel):
    """Entidad anidada dentro de ProyectoResult (para display)."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]  # tipo_documento: RUC o DNI
    nombre: Optional[str]  # nombre_completo


class EntidadConNumeroDocumentoData(BaseModel):
    """Entidad anidada con numero_documento para listado de proyectos."""
    id: Optional[uuid.UUID]
    tipo_documento: Optional[str]  # RUC o DNI
    numero_documento: Optional[str]
    nombre: Optional[str]  # nombre_completo


class EntidadInlineData(BaseModel):
    """
    Entidad inline para crear proyecto inline.

    Se usa dentro de ProyectoInlineData para crear o encontrar
    una Entidad por numero_documento (upsert).

    Args:
        tipo_documento: Tipo de documento (RUC o DNI)
        numero_documento: Número de documento (único, para upsert)
        razon_social: Razón social o nombre completo
        NOTA: nombre_propietario NO pertenece a Entidad — pertenece a ProyectoInlineData
    """
    tipo_documento: str = Field(..., description="Tipo de documento: RUC o DNI")
    numero_documento: str = Field(..., description="Número de documento (RUC 11 dígitos o DNI 8 dígitos)")
    razon_social: str = Field(..., description="Razón social para RUC o nombre completo para DNI")


class EdificacionData(BaseModel):
    """Datos de una edificación para listado de proyectos."""
    id: uuid.UUID
    public_id: str
    numero_revision: int
    estado: str
    fecha_registro: str
    total: Decimal
    tipo_tramite: str
    tramite_accion: str


class LiquidacionesData(BaseModel):
    """Wrapper de liquidaciones para proyecto (sin total_edificaciones)."""
    edificaciones: list[EdificacionData] = Field(default_factory=list)


class ProyectoConLiquidacionesData(BaseModel):
    """Proyecto con liquidaciones anidadas para listado paginado."""
    id: uuid.UUID
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # Nombre del distrito
    entidad: Optional[EntidadConNumeroDocumentoData]
    liquidaciones: LiquidacionesData


class ProyectoCreateData(BaseModel):
    """Datos para crear un proyecto."""
    denominacion: str
    direccion: Optional[str] = None
    distrito_id: Optional[uuid.UUID] = None
    entidad_id: Optional[uuid.UUID] = None


class ProyectoResult(BaseModel):
    """Resultado de operación con proyecto."""
    id: uuid.UUID
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # Nombre del distrito para display
    distrito_id: Optional[uuid.UUID]  # ID del distrito
    entidad: Optional[EntidadSimpleData]

    # NOTE: proyectista fue removido de Proyecto — ahora vive en LiquidacionEdificaciones.proyectistas M2M


class ProyectoPaginatedResult(BaseModel):
    """Resultado paginado para listado de proyectos con liquidaciones."""
    items: list[ProyectoConLiquidacionesData]
    total: int


class ProyectoInlineData(BaseModel):
    """
    DTO para datos inline de proyecto en creación de liquidación.

    Se usa cuando el proyecto no existe y se crea en línea durante
    la primera revisión de una liquidación de edificación.

    Args:
        denominacion: Nombre/denominación del proyecto
        direccion: Dirección opcional del proyecto
        distrito_id: ID del distrito opcional (UUID)
        nombre_propietario: Nombre del propietario o representante legal (requerido)
        entidad: Entidad inline con tipo_documento, numero_documento y razon_social.
                 Se hace upsert por numero_documento.
    """
    denominacion: str
    direccion: Optional[str] = None
    distrito_id: Optional[uuid.UUID] = None
    nombre_propietario: str = Field(..., description="Nombre del propietario o representante legal (requerido)")
    entidad: EntidadInlineData
