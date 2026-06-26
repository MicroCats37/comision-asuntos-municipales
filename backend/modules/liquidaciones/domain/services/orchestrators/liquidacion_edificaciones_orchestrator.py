"""
LiquidacionesEdificacionesOrchestrator — fachada asíncrona ligera para controladores.

Solo delega a LiquidacionesEdificacionesFlujo. Sin lógica de negocio aquí.
"""
from typing import Union
from injector import inject

from ..flujos.liquidacion_edificaciones_flujo import LiquidacionesEdificacionesFlujo
from ...schemas import (
    LiquidacionEdificacionesResult,
    NuevaRevisionFormularioResult,
    LiquidacionSnapshotResult,
    LiquidacionSnapshotFallbackResult,
    RevisionVigenteResult,
    LiquidacionEdificacionesPaginatedResult,
    CotizacionQuoteData,
    ProyectistaInlineData,
    ContactoInlineData,
    DelegadosVigentesResult,
    EspecialidadBasicaResult,
)


class LiquidacionesEdificacionesOrchestrator:
    """
    Fachada asíncrona ligera — delega lógica a Flujo.

    Inyecta flujo vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: LiquidacionesEdificacionesFlujo,
    ):
        self.flujo = flujo

    async def crear_primera_revision(
        self,
        proyecto_public_id: str,
        municipalidad_id: str,
        tipo_tramite: str,
        valor_proyecto: float,
        observacion: str | None,
        revisiones_ids: list[str],
        proyectistas_inline: list[ProyectistaInlineData] | None = None,
        proyectistas_ids: list[str] | None = None,
        delegados_ids: list[str] | None = None,
        contactos_inline: list[ContactoInlineData] | None = None,
    ) -> LiquidacionEdificacionesResult:
        """Crear primera revisión — delega a flujo."""
        return await self.flujo._proceso_primera_revision(
            proyecto_public_id=proyecto_public_id,
            municipalidad_id=municipalidad_id,
            tipo_tramite=tipo_tramite,
            valor_proyecto=valor_proyecto,
            observacion=observacion,
            revisiones_ids=revisiones_ids,
            proyectistas_inline=proyectistas_inline,
            proyectistas_ids=proyectistas_ids,
            delegados_ids=delegados_ids,
            contactos_inline=contactos_inline,
        )

    async def preparar_nueva_revision(
        self,
        liquidacion_previa_id: str,
    ) -> NuevaRevisionFormularioResult:
        """Preparar formulario de nueva revisión — delega a flujo."""
        return await self.flujo._proceso_formulario_nueva_revision(
            liquidacion_previa_id=liquidacion_previa_id,
        )

    async def crear_nueva_revision(
        self,
        liquidacion_previa_id: str,
        observacion: str | None,
        revisiones_ids: list[str],
        proyectistas_inline: list[ProyectistaInlineData] | None = None,
        proyectistas_ids: list[str] | None = None,
        delegados_ids: list[str] | None = None,
        contactos_inline: list[ContactoInlineData] | None = None,
    ) -> LiquidacionEdificacionesResult:
        """Crear nueva revisión — delega a flujo."""
        return await self.flujo._proceso_nueva_revision(
            liquidacion_previa_id=liquidacion_previa_id,
            observacion=observacion,
            revisiones_ids=revisiones_ids,
            proyectistas_inline=proyectistas_inline,
            proyectistas_ids=proyectistas_ids,
            delegados_ids=delegados_ids,
            contactos_inline=contactos_inline,
        )

    async def obtener_liquidacion(
        self,
        liquidacion_id: str,
    ) -> dict:
        """
        Obtener detalle/snapshot de liquidación — delega a flujo.
        Retorna el dict raw del snapshot (sin validación Pydantic) para
        preservar todos los campos almacenados en LiquidacionSnapshot.data.
        """
        return await self.flujo._proceso_obtener_liquidacion(
            liquidacion_id=liquidacion_id,
        )

    async def listar_liquidaciones(
        self,
        page: int,
        page_size: int,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas — delega a flujo."""
        return await self.flujo.listar_liquidaciones_paginado(page=page, page_size=page_size)

    async def obtener_revisiones_vigentes(self) -> list[RevisionVigenteResult]:
        """
        Obtiene todas las revisiones vigentes para mostrar en formulario.
        Retorna lista tipada de RevisionVigenteResult.
        """
        return await self.flujo.obtener_revisiones_vigentes()

    async def listar_snapshots(
        self,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """
        Lista snapshots completos de liquidaciones con paginación.
        Retorna (items_dicts, total).
        """
        return await self.flujo.listar_snapshots_paginado(page, page_size)

    async def cotizar_primera_revision(
        self,
        proyecto_public_id: str,
        valor_proyecto: float,
    ) -> CotizacionQuoteData:
        """Cotizar primera revisión (sin guardar en BD) — delega a flujo."""
        return await self.flujo._proceso_cotizar_primera_revision(
            proyecto_public_id=proyecto_public_id,
            valor_proyecto=valor_proyecto,
        )

    async def cotizar_nueva_revision(
        self,
        liquidacion_previa_id: str,
        revisiones_ids: list[str],
    ) -> CotizacionQuoteData:
        """Cotizar nueva revisión (sin guardar en BD) — delega a flujo."""
        return await self.flujo._proceso_cotizar_nueva_revision(
            liquidacion_previa_id=liquidacion_previa_id,
            revisiones_ids=revisiones_ids,
        )

    async def obtener_delegados_vigentes(
        self,
        municipalidad_id: str,
        revision_id: str | None = None,
        categoria: str | None = None,
    ) -> DelegadosVigentesResult:
        """
        Obtiene delegados vigentes para una municipalidad.

        Delegates to flujo._proceso_delegados_vigentes.
        Retorna DelegadosVigentesResult con lista tipada de delegados.

        Args:
            municipalidad_id: UUID de la municipalidad
            revision_id: UUID opcional de EdificacionesRevision para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas). Default: Edificaciones
        """
        return await self.flujo._proceso_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            revision_id=revision_id,
            categoria=categoria,
        )

    async def obtener_especialidades_vigentes(self) -> list[EspecialidadBasicaResult]:
        """
        Obtiene las especialidades vigentes del grupo EdificacionesEspecialidades.

        Retorna lista tipada de EspecialidadBasicaResult.
        """
        return await self.flujo._proceso_especialidades_vigentes()
