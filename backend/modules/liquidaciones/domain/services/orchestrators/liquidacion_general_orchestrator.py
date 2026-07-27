"""
LiquidacionesGeneralOrchestrator — fachada asíncrona ligera para controladores.

Solo delega a LiquidacionesGeneralFlujo. Sin lógica de negocio aquí.

Patrón: El orquestador recibe el request, valida los parámetros básicos,
y delega al flujo para la ejecución.
"""
from injector import inject
from ninja.errors import HttpError

from ..flujos.liquidacion_general_flujo import LiquidacionesGeneralFlujo
from ...schemas import LiquidacionGeneralPaginatedResult, LiquidacionGeneralResult, LiquidacionGeneralListItem
from ...schemas import EspecialidadBasicaResult, DelegadosVigentesResult, InspectoresVigentesResult


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
        liquidacion_id: str | None = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Lista liquidaciones paginadas — delega a flujo.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página (max 100)
            tipo_liquidacion: Filtro opcional por tipo de liquidación
            liquidacion_id: Filtro opcional por ID de liquidación

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
            liquidacion_id=liquidacion_id,
        )

    async def obtener_liquidacion_list_item_por_id(
        self,
        liquidacion_id: str,
    ) -> LiquidacionGeneralListItem:
        """
        Obtiene una liquidación por ID retornando el mismo LiquidacionGeneralListItem
        que la lista — con todos los datos ricos (proyectistas, delegados, revisiones, etc.).

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneralListItem con datos completos

        Raises:
            HttpError(404): Si la liquidación no existe
        """
        result = await self.flujo._proceso_listar_liquidaciones(
            page=1,
            page_size=1,
            liquidacion_id=liquidacion_id,
        )

        if not result.items:
            raise HttpError(404, f"Liquidación con ID '{liquidacion_id}' no encontrada.")

        return result.items[0]

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

    async def obtener_especialidades_vigentes_por_tipo(
        self,
        tipo_liquidacion: str,
    ) -> list[EspecialidadBasicaResult]:
        """
        Obtiene las especialidades vigentes para un tipo de liquidación dado.

        Args:
            tipo_liquidacion: Slug (ej. "habilitacion-urbana") o enum (ej. "HABILITACION_URBANA")

        Returns:
            Lista de EspecialidadBasicaResult con id y nombre. Empty list si no hay grupo vigente.
        """
        return await self.flujo._proceso_especialidades_vigentes_por_tipo(
            tipo_liquidacion=tipo_liquidacion,
        )

    async def obtener_delegados_vigentes(
        self,
        municipalidad_id: str,
        tipo_liquidacion: str,
        revision_id: str,
        categoria: str | None = None,
    ) -> DelegadosVigentesResult:
        return await self.flujo._proceso_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            tipo_liquidacion=tipo_liquidacion,
            revision_id=revision_id,
            categoria=categoria,
        )

    async def obtener_inspectores_vigentes(self, liquidacion_id: str) -> InspectoresVigentesResult:
        return await self.flujo._proceso_inspectores_vigentes(liquidacion_id=liquidacion_id)

    async def obtener_inspectores_vigentes_por_tipo(self, tipo_liquidacion: str) -> InspectoresVigentesResult:
        return await self.flujo._proceso_inspectores_vigentes_por_tipo(tipo_liquidacion=tipo_liquidacion)

    async def obtener_inspectores_vigentes_por_liquidacion_previa(
        self, liquidacion_previa_id: str
    ) -> InspectoresVigentesResult:
        return await self.flujo._proceso_inspectores_vigentes_por_liquidacion_previa(
            liquidacion_previa_id=liquidacion_previa_id
        )

    async def buscar_liquidaciones_por_documento_entidad(
        self,
        numero_documento: str,
        tipos_liquidacion: list[str],
        page: int = 1,
        page_size: int = 10,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Busca liquidaciones por número de documento de entidad y tipos de liquidación.

        Args:
            numero_documento: DNI o RUC de la entidad asociada al proyecto.
            tipos_liquidacion: Lista de tipos de liquidación a filtrar (ej. ["EDIFICACION", "HABILITACION_URBANA"]).
            page: Número de página (1-indexed).
            page_size: Elementos por página.

        Returns:
            LiquidacionGeneralPaginatedResult con items y total.
        """
        return await self.flujo._proceso_buscar_liquidaciones_por_documento_entidad(
            numero_documento=numero_documento,
            tipos_liquidacion=tipos_liquidacion,
            page=page,
            page_size=page_size,
        )
