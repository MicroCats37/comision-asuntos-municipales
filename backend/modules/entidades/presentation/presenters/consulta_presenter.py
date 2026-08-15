"""
ConsultaPresenter — transforma resultados de consulta externa a esquemas HTTP.

Transforma ConsultaDocumentoResult a schema de respuesta HTTP.
"""

from modules.entidades.domain.results import ConsultaDocumentoResult
from modules.entidades.presentation.schemas.consulta_schemas import DocumentoConsultaOut


class ConsultaPresenter:
    """
    Transforma objetos de resultado de consulta externa a esquemas de respuesta HTTP.

    Patrón: Controller → Orchestrator → Presenter → HTTP Schema
    """

    @staticmethod
    def present_documento(result: ConsultaDocumentoResult) -> DocumentoConsultaOut:
        """
        Transforma el resultado unificado de consulta a esquema HTTP minimal.

        Args:
            result: ConsultaDocumentoResult del orchestrator

        Returns:
            DocumentoConsultaOut schema para respuesta HTTP
        """
        return DocumentoConsultaOut(
            tipo_documento=result.tipo_documento,
            numero_documento=result.numero_documento,
            razon_social=result.razon_social,
        )
