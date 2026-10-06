"""
Domain schemas — DTOs internos para servicios de Entidades.
"""
import uuid
from pydantic import BaseModel
from typing import Optional


class EntidadCreateData(BaseModel):
    """Datos para crear una entidad."""
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None


class EntidadResult(BaseModel):
    """Resultado de operación con entidad."""
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    razon_social: Optional[str]
    nombre_completo: str
    direccion: Optional[str]
