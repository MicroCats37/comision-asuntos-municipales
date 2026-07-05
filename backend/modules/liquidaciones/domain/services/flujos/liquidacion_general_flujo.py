"""
Liquidaciones General Flujo — flujos async para operaciones generales de liquidaciones.

Cada método _proceso_* es un caso de uso completo.
Usa sync_to_async para envolver operaciones ORM del core service.

Este flujo es ligero ya que las operaciones de lista/detalle no requieren
lógica de negocio compleja — solo consulta datos existentes.
"""
from __future__ import annotations

from typing import Optional

from asgiref.sync import sync_to_async

from ..core.liquidaciones_general_core import LiquidacionesGeneralService
from ...schemas import LiquidacionGeneralPaginatedResult, LiquidacionGeneralResult


class LiquidacionesGeneralFlujo:
    """
    Flujos async para operaciones de Liquidaciones Generales.

    Solo proporciona listados y detalles de liquidaciones existentes.
    No crea ni modifica registros.
    """

    @property
    def core(self) -> LiquidacionesGeneralService:
        """Acceso lazy al servicio core."""
        if not hasattr(self, '_core'):
            self._core = LiquidacionesGeneralService()
        return self._core

    async def _proceso_listar_liquidaciones(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: Optional[str] = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Proceso para listar liquidaciones con paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página
            tipo_liquidacion: Filtro opcional por tipo de liquidación

        Returns:
            LiquidacionGeneralPaginatedResult con items y total
        """
        return await sync_to_async(
            self.core._listar_liquidaciones_paginado_result
        )(page=page, page_size=page_size, tipo_liquidacion=tipo_liquidacion)

    async def _proceso_obtener_liquidacion_detalle(
        self,
        liquidacion_id: str,
    ) -> Optional[LiquidacionGeneralResult]:
        """
        Proceso para obtener el detalle de una liquidación por ID.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneralResult o None si no existe
        """
        return await sync_to_async(
            self.core._obtener_liquidacion_por_id_result
        )(liquidacion_id=liquidacion_id)
