"""
ConsultaController — controladores HTTP para consulta de datos externos.

 薄 — solo delega a ConsultaOrchestrator y retorna vía ConsultaPresenter.

 Endpoint único:
 - GET /consulta/{documento}: Consulta datos por DNI (8 dígitos) o RUC (11 dígitos)
   Auto-detecta el tipo: 8 → DNI/RENIEC, 11 → RUC/SUNAT.
   Respuesta: { tipo_documento, numero_documento, razon_social }.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Path

from core.responses import ApiResponse, success_response
from modules.entidades.presentation.schemas.consulta_schemas import DocumentoConsultaOut
from modules.entidades.presentation.presenters.consulta_presenter import ConsultaPresenter
from modules.entidades.domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator


@api_controller("/entidades", tags=["Consulta Externa"], permissions=[AllowAny])
class ConsultaController:
    """
    Controlador para consulta de datos externos (RENIEC/SUNAT) unificado.

    薄 — delega todo formatting de respuesta a ConsultaPresenter.
    """

    @inject
    def __init__(
        self,
        orchestrator: ConsultaOrchestrator,
        presenter: ConsultaPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.get("/consulta/{documento}", response={200: ApiResponse[DocumentoConsultaOut]}, auth=None)
    async def consultar_documento(
        self,
        documento: str = Path(
            ...,
            min_length=8,
            max_length=11,
            description="Número de documento: DNI (8 dígitos) o RUC (11 dígitos)",
        ),
    ):
        """
        Consulta datos de documento por número (DNI o RUC).

        Auto-detecta el tipo de documento:
        - 8 dígitos → DNI (RENIEC)
        - 11 dígitos → RUC (SUNAT)

        Args:
            documento: Número de documento (8 o 11 dígitos).

        Returns:
            Datos del documento (tipo_documento, numero_documento, razon_social).

        Raises:
            ReniecNotFoundError (404): Si el DNI no existe.
            SunatNotFoundError (404): Si el RUC no existe.
        """
        result = await self.orchestrator.consultar_documento(documento)
        return success_response(
            self.presenter.present_documento(result)
        )
