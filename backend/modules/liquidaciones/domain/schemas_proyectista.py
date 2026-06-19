"""
Domain schemas — DTOs internos para servicios de Proyectista.
"""
import uuid
from pydantic import BaseModel
from typing import Optional


class ProyectistaCreateData(BaseModel):
    """Datos para crear un proyectista."""
    nombres: str
    apellidos: str
    cip: Optional[str] = None
    dni: Optional[str] = None
    cap: Optional[str] = None


class ProyectistaResult(BaseModel):
    """Resultado de operación con proyectista."""
    id: uuid.UUID
    nombres: str
    apellidos: str
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]
