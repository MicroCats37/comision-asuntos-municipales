"""
Liquidaciones General Flujo — flujos async para operaciones generales de liquidaciones.

Cada método _proceso_* es un caso de uso completo.
Usa sync_to_async para envolver operaciones ORM del core service.

Este flujo es ligero ya que las operaciones de lista/detalle no requieren
lógica de negocio compleja — solo consulta datos existentes.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from asgiref.sync import sync_to_async

from ..core.liquidaciones_general_core import LiquidacionesGeneralService
from ...schemas import LiquidacionGeneralPaginatedResult, LiquidacionGeneralResult
from ...schemas import EspecialidadBasicaResult, DelegadosVigentesResult, InspectoresVigentesResult


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
        liquidacion_id: Optional[str] = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Proceso para listar liquidaciones con paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página
            tipo_liquidacion: Filtro opcional por tipo de liquidación
            liquidacion_id: Filtro opcional por ID de liquidación

        Returns:
            LiquidacionGeneralPaginatedResult con items y total
        """
        return await sync_to_async(
            self.core._listar_liquidaciones_paginado_result
        )(page=page, page_size=page_size, tipo_liquidacion=tipo_liquidacion, liquidacion_id=liquidacion_id)

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

    async def _proceso_especialidades_vigentes_por_tipo(
        self,
        tipo_liquidacion: str,
    ) -> list[EspecialidadBasicaResult]:
        """
        Obtiene las especialidades vigentes para un tipo de liquidación dado.

        Fuente: grupo EspecialidadesLiquidacion cuyo tipo_liquidacion corresponde
        al parámetro, periodo_inicio <= hoy y (periodo_fin IS NULL OR periodo_fin >= hoy).

        Args:
            tipo_liquidacion: Slug (ej. "habilitacion-urbana") o enum (ej. "HABILITACION_URBANA")

        Returns:
            Lista de EspecialidadBasicaResult con id y nombre. Empty list si no hay grupo vigente.
        """
        from datetime import date
        from django.db.models import Q
        from ...models import EspecialidadesLiquidacion
        from ...constants import normalizar_tipo_liquidacion

        today = date.today()
        tipo_normalizado = normalizar_tipo_liquidacion(tipo_liquidacion)

        grupo_vigente = await sync_to_async(
            EspecialidadesLiquidacion.objects.filter(
                tipo_liquidacion=tipo_normalizado,
                periodo_inicio__lte=today,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today)
            ).first
        )()

        if not grupo_vigente:
            return []

        def _sync_get_especialidades():
            return [
                EspecialidadBasicaResult(id=esp.id, nombre=esp.nombre)
                for esp in grupo_vigente.especialidades.all()
            ]

        return await sync_to_async(_sync_get_especialidades)()

    async def _proceso_delegados_vigentes(
        self,
        municipalidad_id: str,
        tipo_liquidacion: str,
        revision_id: str,
        categoria: str | None = None,
    ) -> DelegadosVigentesResult:
        from ...constants import CategoriaDelegado, normalizar_tipo_liquidacion

        today = date.today()
        tipo_normalizado = normalizar_tipo_liquidacion(tipo_liquidacion)

        if not categoria:
            categoria_por_tipo = {
                "EDIFICACION": CategoriaDelegado.EDIFICACIONES,
                "HABILITACION_URBANA": CategoriaDelegado.HABILITACIONES_URBANAS,
            }
            categoria = categoria_por_tipo.get(tipo_normalizado)

        delegados = await sync_to_async(self.core._obtener_delegados_vigentes)(
            municipalidad_id=municipalidad_id,
            fecha=today,
            tipo_liquidacion=tipo_normalizado,
            revision_id=revision_id,
            categoria=categoria,
        )

        return DelegadosVigentesResult(delegados=delegados)

    async def _proceso_inspectores_vigentes(self, liquidacion_id: str) -> InspectoresVigentesResult:
        from datetime import date
        from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import liquidacion_inspector_core

        inspectores = await sync_to_async(liquidacion_inspector_core._obtener_inspectores_vigentes)(
            liquidacion_id=liquidacion_id,
            fecha=date.today(),
        )
        return InspectoresVigentesResult(inspectores=inspectores)

    async def _proceso_inspectores_vigentes_por_tipo(self, tipo_liquidacion: str) -> InspectoresVigentesResult:
        """Obtiene inspectores vigentes para un tipo de liquidacion (sin exclusion por liquidacion existente)."""
        from datetime import date
        from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import liquidacion_inspector_core

        inspectores = await sync_to_async(liquidacion_inspector_core._obtener_inspectores_vigentes_por_tipo)(
            tipo_liquidacion=tipo_liquidacion,
            fecha=date.today(),
        )
        return InspectoresVigentesResult(inspectores=inspectores)

    async def _proceso_inspectores_vigentes_por_liquidacion_previa(
        self, liquidacion_previa_id: str
    ) -> InspectoresVigentesResult:
        """
        Obtiene inspectores vigentes y elegibles para una liquidacion previa de IO.

        Deriva el tipo de liquidacion (EDIFICACION o HABILITACION_URBANA) de la
        liquidacion previa y retorna solo inspectores con tipo_liquidacion compatible,
        activos y vigentes. No excluye inspectores ya asociados (para uso en creacion).

        Args:
            liquidacion_previa_id: UUID de la liquidacion previa.

        Returns:
            InspectoresVigentesResult con lista de inspectores elegibles.
        """
        import uuid as uuid_lib
        from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import liquidacion_inspector_core

        liquidacion_uuid = uuid_lib.UUID(liquidacion_previa_id)
        inspectores = await sync_to_async(
            liquidacion_inspector_core._obtener_inspectores_vigentes_por_liquidacion_previa
        )(liquidacion_previa_id=liquidacion_uuid)
        return InspectoresVigentesResult(inspectores=inspectores)

    async def _proceso_buscar_liquidaciones_por_documento_entidad(
        self,
        numero_documento: str,
        tipos_liquidacion: list[str],
        page: int,
        page_size: int,
    ) -> LiquidacionGeneralPaginatedResult:
        """
        Proceso para buscar liquidaciones por número de documento de entidad y tipos.

        Args:
            numero_documento: DNI o RUC de la entidad asociada al proyecto.
            tipos_liquidacion: Lista de tipos de liquidación a filtrar.
            page: Número de página (1-indexed).
            page_size: Elementos por página.

        Returns:
            LiquidacionGeneralPaginatedResult con items y total.
        """
        return await sync_to_async(
            self.core._buscar_liquidaciones_por_documento_entidad
        )(
            numero_documento=numero_documento,
            tipos_liquidacion=tipos_liquidacion,
            page=page,
            page_size=page_size,
        )
