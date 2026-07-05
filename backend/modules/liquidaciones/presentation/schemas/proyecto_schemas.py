"""
Presentation schemas — Esquemas HTTP para Proyectos.

Usa Ninja Schema para request/response.

NOTE: proyectista fue removido de Proyecto — ahora vive en
LiquidacionEdificaciones.proyectistas M2M.
"""
import uuid
from ninja import Schema, Field
from typing import Optional


class EntidadSimpleOut(Schema):
    """Entidad anidada en respuesta (para crear/buscar proyecto)."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]  # tipo_documento: RUC o DNI
    nombre: Optional[str]  # nombre_completo


class EntidadWithNumeroDocumentoOut(Schema):
    """Entidad anidada en respuesta de listado con numero_documento."""
    id: Optional[uuid.UUID]
    tipo_documento: Optional[str]  # RUC o DNI
    numero_documento: Optional[str]
    nombre: Optional[str]  # nombre_completo


class EdificacionListItemOut(Schema):
    """
    Edificación anidada dentro de liquidaciones en listado de proyectos.

    NOTE: No incluye total_edificaciones (conteo de edificaciones).
    """
    id: uuid.UUID
    public_id: str
    numero_revision: int
    estado: str
    fecha_registro: str
    total: float
    tipo_tramite: str
    tramite_accion: str


class LiquidacionesInlineOut(Schema):
    """Liquidaciones anidadas dentro de proyecto (wrapper sin total_edificaciones)."""
    edificaciones: list[EdificacionListItemOut] = Field(default_factory=list)


class ProyectoListItemOut(Schema):
    """Proyecto en respuesta de listado paginado."""
    id: uuid.UUID
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # Nombre del distrito para display
    entidad: Optional[EntidadWithNumeroDocumentoOut]
    liquidaciones: LiquidacionesInlineOut


class ProyectoIn(Schema):
    """Payload para crear proyecto."""
    denominacion: str = Field(..., min_length=1, max_length=255, description="Denominación del proyecto")
    direccion: Optional[str] = Field(None, max_length=512, description="Dirección del proyecto")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (UUID)")
    entidad_id: Optional[uuid.UUID] = Field(None, description="ID de la entidad (UUID)")


class ProyectoOut(Schema):
    """Proyecto en respuesta."""
    id: uuid.UUID
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # Nombre del distrito para display
    distrito_id: Optional[uuid.UUID]  # ID del distrito
    entidad: Optional[EntidadSimpleOut]


class ProyectoUpsertResponseOut(Schema):
    """Respuesta de crear/buscar proyecto."""
    id: uuid.UUID
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # Nombre del distrito para display
    distrito_id: Optional[uuid.UUID]  # ID del distrito
    entidad: Optional[EntidadSimpleOut]
