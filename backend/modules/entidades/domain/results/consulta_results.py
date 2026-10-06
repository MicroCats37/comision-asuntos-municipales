"""
Consulta Results - DTO unificado para consulta de documentos (DNI/RUC).

Unified result dataclass para consulta de documentos por número (DNI o RUC).
"""
from dataclasses import dataclass


@dataclass
class ConsultaDocumentoResult:
    """
    Resultado unificado de consulta por número de documento.

    semantics:
      - Para RUC (11 dígitos): razon_social = razón social de la institución
      - Para DNI (8 dígitos): razon_social = nombre_completo = "APELLIDOS, NOMBRES"
      - Para长度 inválida: tipo_documento = "DESCONOCIDO"
    """
    tipo_documento: str  # "DNI" | "RUC" | "DESCONOCIDO"
    numero_documento: str
    razon_social: str
