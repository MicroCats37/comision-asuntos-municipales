"""
Presentation schemas — Esquemas HTTP para Proyectistas.

Usa Ninja Schema para request/response.

NOTE: Los esquemas fueron simplificados para usar PerfilIngeniero referenciado
en lugar de campos de identidad duplicados.
"""
import uuid
from ninja import Schema, Field
from typing import Optional


class ProyectistaIn(Schema):
    """Payload para crear/buscar proyectista por perfil y especialidad."""
    perfil_ingeniero_id: uuid.UUID = Field(..., description="ID del PerfilIngeniero")
    especialidad_id: uuid.UUID = Field(..., description="ID de la Especialidad")
    descripcion: Optional[str] = Field(None, description="Descripción opcional")


class ProyectistaOut(Schema):
    """Proyectista en respuesta."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None


class ProyectistaUpsertResponseOut(Schema):
    """Respuesta de crear/buscar proyectista."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None
    creado: bool  # True si se creó, False si se encontró existente
