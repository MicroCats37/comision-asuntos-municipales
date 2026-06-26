"""
IngenieroHabilitadoFlujo — flujos async para verificación de ingeniero habilitado CIP.
"""
from asgiref.sync import sync_to_async
from injector import inject

from ..core.perfil_ingeniero_core_service import PerfilIngenieroCoreService
from ...schemas.ingeniero_habilitado_schemas import CipColegiadoData, IngenieroHabilitadoResult
from ....infrastructure.services import ICipClient, CipServiceUnavailableError


class IngenieroHabilitadoFlujo:
    """
    Flujos async para verificar ingeniero habilitado via CIP.

    Caso de uso: GET /ingenieros/habilitados/{cip}
    - Llama al endpoint CIP externo
    - Retorna datos estructurados con habilitado = (condicion == '1')
    - NO crea ni actualiza PerfilIngeniero en este flujo (solo lectura/validación)
    """

    @inject
    def __init__(
        self,
        cip_client: ICipClient,
        core: PerfilIngenieroCoreService,
    ):
        self._cip_client = cip_client
        self._core = core

    def _normalizar_cip(self, cip: str) -> str:
        """Normaliza CIP a 6 dígitos."""
        return self._core._normalizar_cip(cip)

    async def _proceso_obtener_ingeniero_habilitado(
        self,
        cip: str,
    ) -> IngenieroHabilitadoResult:
        """
        Proceso para obtener ingeniero habilitado por CIP.

        1. Normaliza el CIP
        2. Llama al endpoint CIP externo
        3. Mapea respuesta a schema estructurado
        4. Retorna con habilitado = (condicion == '1')

        NOTE: Este flujo es de SOLO LECTURA/VALIDACIÓN. No crea ni actualiza
        PerfilIngeniero en la base de datos.

        Args:
            cip: Número de CIP

        Returns:
            IngenieroHabilitadoResult con datos del ingeniero y flag habilitado

        Raises:
            CipNotFoundError: Si el CIP no existe en el servicio externo
            CipServiceUnavailableError: Si el servicio CIP no está disponible
        """
        normalized_cip = self._normalizar_cip(cip)
        if not normalized_cip:
            from core.exceptions import NotFoundError
            raise NotFoundError(f"CIP inválido: {cip}")

        # Llamar al cliente CIP (puede ser real o simulador)
        try:
            raw_data = await sync_to_async(self._cip_client.get_colegiado)(normalized_cip)
        except CipServiceUnavailableError:
            raise

        if raw_data is None:
            from core.exceptions import CipNotFoundError
            raise CipNotFoundError(cip=normalized_cip)

        # Mapear a CipColegiadoData
        cip_data = CipColegiadoData(**raw_data)

        # Construir resultado
        return IngenieroHabilitadoResult.from_cip_data(cip_data)
