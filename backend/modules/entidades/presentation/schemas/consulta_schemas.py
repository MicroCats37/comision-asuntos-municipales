"""
Presentation Schemas — Esquemas HTTP para consulta externa.

Schemas unificados para consulta de datos de instituciones (SUNAT) y personas (RENIEC).
Respuesta minimal: solo tipo_documento, numero_documento, razon_social.
"""

from ninja import Field
from core.types import BaseSchema


class DocumentoConsultaOut(BaseSchema):
    """
    Respuesta unificada para consulta de documento (DNI o RUC).

    semantics:
      - tipo_documento: "DNI" | "RUC" | "DESCONOCIDO"
      - numero_documento: el número enviado
      - razon_social: para RUC = razón social; para DNI = "APELLIDOS, NOMBRES"
    """
    tipo_documento: str = Field(..., description="Tipo: DNI, RUC o DESCONOCIDO")
    numero_documento: str = Field(..., description="Número de documento enviado")
    razon_social: str = Field(..., description="Razón social (institución) o nombre completo (persona)")