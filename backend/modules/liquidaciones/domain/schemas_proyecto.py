"""
Domain schemas — DTOs internos para servicios de Proyecto.
"""
import uuid
from pydantic import BaseModel
from typing import Optional


class EntidadSimpleData(BaseModel):
    """Entidad anidada dentro de ProyectoResult (para display)."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]  # tipo_documento: RUC o DNI
    nombre: Optional[str]  # nombre_completo


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
