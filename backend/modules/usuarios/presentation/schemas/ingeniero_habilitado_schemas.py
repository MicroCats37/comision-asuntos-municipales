"""
Presentation schemas — Esquemas HTTP para Ingeniero/Habilitación CIP.
"""
from ninja import Field
from typing import Optional
from core.types import BaseSchema


class IngenieroHabilitadoOut(BaseSchema):
    """
    Schema de respuesta SIMPLIFICADO para GET /ingenieros/habilitados/{cip}.

    Respuesta minimal para el frontend con solo los campos necesarios:
    - cip: número de CIP
    - nombres: nombre1 + nombre2 combinados y limpios
    - apellidos: paterno + materno combinados y limpios
    - habilitado: true si condicion == '1'
    - capitulo: descripción del capítulo como string

    NOTE: El dominio CipColegiadoData/IngenieroHabilitadoResult se mantiene completo
    para uso interno (PerfilIngeniero upsert, validación de liquidaciones).
    Esta simplificación es SOLO para la respuesta HTTP.
    """
    cip: str = Field(..., description="Número de CIP (6 dígitos)")
    nombres: str = Field(..., description="Nombres completos (nombre1 + nombre2, sin espacios extra)")
    apellidos: str = Field(..., description="Apellidos completos (paterno + materno, sin espacios extra)")
    habilitado: bool = Field(..., description="True si condicion == '1'")
    capitulo: Optional[str] = Field(None, description="Descripción del capítulo profesional")
