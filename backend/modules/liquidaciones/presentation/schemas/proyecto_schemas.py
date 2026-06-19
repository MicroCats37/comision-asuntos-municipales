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
    """Entidad anidada en respuesta."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]


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
