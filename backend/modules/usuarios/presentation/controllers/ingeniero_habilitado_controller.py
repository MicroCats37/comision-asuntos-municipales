"""
IngenieroHabilitadoController — controlador HTTP ligero para endpoints de ingeniero habilitado CIP.

Solo delega a IngenieroHabilitadoOrchestrator y retorna la respuesta.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.usuarios.presentation.schemas.ingeniero_habilitado_schemas import IngenieroHabilitadoOut
from modules.usuarios.presentation.presenters.ingeniero_habilitado_presenter import IngenieroHabilitadoPresenter
from modules.usuarios.domain.services.orchestrators.ingeniero_habilitado_orchestrator import IngenieroHabilitadoOrchestrator


@api_controller("/ingenieros", tags=["Ingenieros"], permissions=[AllowAny])
class IngenieroHabilitadoController:
    """
    Controlador para verificación de ingenieros habilitados via CIP.

    Endpoints:
    - GET /habilitados/{cip}: Obtiene datos del ingeniero con flag habilitado
    """

    @inject
    def __init__(self, orchestrator: IngenieroHabilitadoOrchestrator):
        self.orchestrator = orchestrator

    @route.get("/habilitados/{cip}", response={200: ApiResponse[IngenieroHabilitadoOut]}, auth=None)
    async def obtener_ingeniero_habilitado(self, cip: str):
        """
        Obtiene datos del ingeniero habilitado por CIP.

        Llama al servicio externo CIP y retorna los datos estructurados incluyendo
        el flag `habilitado` computado como `condicion == '1'`.

        Este endpoint es de SOLO LECTURA/VALIDACIÓN. No crea ni actualiza
        PerfilIngeniero en la base de datos.

        Args:
            cip: Número de CIP (6 dígitos)

        Returns:
            Datos del ingeniero con flag habilitado
        """
        result = await self.orchestrator.obtener_ingeniero_habilitado(cip=cip)
        # Presenter transforma explícitamente el result del dominio al schema HTTP
        # (incluye conversión de fechaNacimiento: date → str YYYY-MM-DD)
        presented = IngenieroHabilitadoPresenter.present(result)
        return success_response(presented)
