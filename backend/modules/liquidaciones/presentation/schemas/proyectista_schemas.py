"""
Presentation schemas — Esquemas HTTP para Proyectistas.

Usa Ninja Schema para request/response.
"""
import uuid
from ninja import Schema, Field
from typing import Optional


class ProyectistaIn(Schema):
    """Payload para crear/buscar proyectista."""
    nombres: str = Field(..., min_length=1, max_length=255, description="Nombres")
    apellidos: str = Field(..., min_length=1, max_length=255, description="Apellidos")
    cip: Optional[str] = Field(None, max_length=6, description="CIP (6 dígitos)")
    dni: Optional[str] = Field(None, max_length=8, description="DNI (8 dígitos)")
    cap: Optional[str] = Field(None, max_length=6, description="CAP (6 dígitos)")


class ProyectistaOut(Schema):
    """Proyectista en respuesta."""
    id: uuid.UUID
    nombres: str
    apellidos: str
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]


class ProyectistaUpsertResponseOut(Schema):
    """Respuesta de crear/buscar proyectista."""
    id: uuid.UUID
    nombres: str
    apellidos: str
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]
    creado: bool  # True si se creó, False si se encontró existente
