"""
ConsultaController — controladores HTTP para consulta de datos externos.

薄 — solo delega a ConsultaOrchestrator y retorna vía ConsultaPresenter.

Endpoints:
- GET /consulta-sunat/{ruc}: Consulta datos de institución por RUC
- GET /consulta-reniec/{dni}: Consulta datos de persona por DNI
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Path

from core.responses import ApiResponse, success_response
from modules.entidades.presentation.schemas.consulta_schemas import InstitucionSunatOut, PersonaReniecOut
from modules.entidades.presentation.presenters.consulta_presenter import ConsultaPresenter
from modules.entidades.domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator


@api_controller("/entidades", tags=["Consulta Externa"], permissions=[AllowAny])
class ConsultaController:
    """
    Controlador para consulta de datos externos (SUNAT/RENIEC).

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

    @route.get("/consulta-sunat/{ruc}", response={200: ApiResponse[InstitucionSunatOut]}, auth=None)
    async def consultar_sunat(
        self,
        ruc: str = Path(..., min_length=11, max_length=11, description="RUC (11 dígitos)"),
    ):
        """
        Consulta datos de una institución por RUC usando el servicio SUNAT.

        Args:
            ruc: Número de RUC (11 dígitos).

        Returns:
            Datos de la institución (razón social, estado, dirección, etc.).

        Raises:
            SunatNotFoundError (404): Si el RUC no existe.
        """
        result = await self.orchestrator.consultar_sunat(ruc)
        return success_response(
            self.presenter.present_sunat(result)
        )

    @route.get("/consulta-reniec/{dni}", response={200: ApiResponse[PersonaReniecOut]}, auth=None)
    async def consultar_reniec(
        self,
        dni: str = Path(..., min_length=8, max_length=8, description="DNI (8 dígitos)"),
    ):
        """
        Consulta datos de una persona por DNI usando el servicio RENIEC.

        Args:
            dni: Número de DNI (8 dígitos).

        Returns:
            Datos de la persona (nombres, apellidos, fecha nacimiento, etc.).

        Raises:
            ReniecNotFoundError (404): Si el DNI no existe.
        """
        result = await self.orchestrator.consultar_reniec(dni)
        return success_response(
            self.presenter.present_reniec(result)
        )