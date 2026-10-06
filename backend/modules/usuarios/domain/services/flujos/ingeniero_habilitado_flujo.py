"""
IngenieroHabilitadoFlujo — flujos async para verificación de ingeniero habilitado CIP.
"""
import logging

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject

from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService
from modules.usuarios.domain.services.core.ingeniero_habilitacion_core_service import IngenieroHabilitacionCoreService
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData, IngenieroHabilitadoResult
from modules.usuarios.infrastructure.services import ICipClient, CipServiceUnavailableError

logger = logging.getLogger(__name__)


class IngenieroHabilitadoFlujo:
    """
    Flujos async para verificar ingeniero habilitado via CIP.

    Caso de uso: GET /ingenieros/habilitados/{cip}
    - Llama al endpoint CIP externo
    - Retorna datos estructurados con habilitado = (condicion == '1')
    - Registra la búsqueda con deduplicación diaria (efecto secundario invisible)
    """

    @inject
    def __init__(
        self,
        cip_client: ICipClient,
        core: PerfilIngenieroCoreService,
        habilitacion_core: IngenieroHabilitacionCoreService,
    ):
        self._cip_client = cip_client
        self._core = core
        self._habilitacion_core = habilitacion_core

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

        NOTE: Este flujo tiene efecto secundario: registra la búsqueda con
        deduplicación diaria en IngenieroHabilitacion y crea/actualiza
        PerfilIngeniero con los datos obtenidos del CIP. El efecto secundario
        es aceptable (no debe fallar la respuesta HTTP).

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

        # Registrar la búsqueda con deduplicación diaria (efecto secundario invisible)
        # Solo búsquedas exitosas: CIP encontrado + datos obtenidos
        await self._registrar_busqueda_async(normalized_cip, cip_data)

        # Construir resultado
        return IngenieroHabilitadoResult.from_cip_data(cip_data)

    async def _registrar_busqueda_async(
        self,
        normalized_cip: str,
        cip_data: CipColegiadoData,
    ) -> None:
        """
        Registra la búsqueda de ingeniero habilitado de forma asíncrona.

        Efecto secundario invisible: no debe romper la respuesta del endpoint.
        Si el registro falla, se loguea el error y se continúa.

        Args:
            normalized_cip: CIP normalizado (6 dígitos)
            cip_data: Datos mapeados del endpoint CIP
        """
        try:

            @sync_to_async
            def _atomic_registrar():
                with transaction.atomic():
                    # Obtener o crear PerfilIngeniero por CIP (delegado al Core)
                    perfil = self._core.obtener_o_crear_perfil_por_cip(normalized_cip)

                    # Registrar la búsqueda con deduplicación diaria
                    self._habilitacion_core.registrar_busqueda(
                        perfil_ingeniero=perfil,
                        condicion_cip=cip_data.condicion,
                        ultimo_periodo_pagado_cip=cip_data.ultimoPeriodoPagado,
                    )

            await _atomic_registrar()
        except Exception:
            # NO debe romper la respuesta del endpoint
            logger.exception(
                f"Error al registrar búsqueda de ingeniero habilitado CIP {normalized_cip}"
            )
