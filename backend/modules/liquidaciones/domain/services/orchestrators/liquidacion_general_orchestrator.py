"""
LiquidacionesGeneralOrchestrator — fachada asíncrona ligera para controladores.

Solo delega a LiquidacionesGeneralFlujo. Sin lógica de negocio aquí.

Patrón: El orquestador recibe el request, valida los parámetros básicos,
y delega al flujo para la ejecución.
"""
from injector import inject
from ninja.errors import HttpError

from ..flujos.liquidacion_general_flujo import LiquidacionesGeneralFlujo
from ...schemas import LiquidacionGeneralPaginatedResult, LiquidacionGeneralResult


class LiquidacionesGeneralOrchestrator:
    """
    Fachada asíncrona ligera — delega lógica a Flujo.

    Inyecta flujo vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: LiquidacionesGeneralFlujo,
    ):
        self.flujo = flujo

    async def listar_liquidaciones(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: str | None = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Lista liquidaciones paginadas — delega a flujo.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página (max 100)
            tipo_liquidacion: Filtro opcional por tipo de liquidación

        Returns:
            LiquidacionGeneralPaginatedResult con items y total
        """
        # Validación básica de parámetros
        if page < 1:
            raise HttpError(400, "El número de página debe ser mayor o igual a 1.")
        if page_size < 1 or page_size > 100:
            raise HttpError(400, "El tamaño de página debe estar entre 1 y 100.")

        return await self.flujo._proceso_listar_liquidaciones(
            page=page,
            page_size=page_size,
            tipo_liquidacion=tipo_liquidacion,
        )

    async def obtener_liquidacion_por_id(
        self,
        liquidacion_id: str,
    ) -> LiquidacionGeneralResult:
        """
        Obtiene el detalle de una liquidación por ID — delega a flujo.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneralResult con los datos de la liquidación

        Raises:
            HttpError(404): Si la liquidación no existe
        """
        result = await self.flujo._proceso_obtener_liquidacion_detalle(
            liquidacion_id=liquidacion_id,
        )

        if result is None:
            raise HttpError(404, f"Liquidación con ID '{liquidacion_id}' no encontrada.")

        return result
