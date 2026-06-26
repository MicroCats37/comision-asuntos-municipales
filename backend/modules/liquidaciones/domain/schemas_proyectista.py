"""
Domain schemas — DTOs internos para servicios de Proyectista.

NOTE: Este módulo fue simplificado para eliminar campos de identidad duplicados
(nombres, apellidos, cip, dni, cap). La identidad del ingeniero se obtiene
via PerfilIngeniero referenciado.
"""
import uuid
from pydantic import BaseModel
from typing import Optional


class ProyectistaCreateData(BaseModel):
    """Datos para crear/actualizar un proyectista."""
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    especialidad_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = None


class ProyectistaResult(BaseModel):
    """Resultado de operación con proyectista."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None
