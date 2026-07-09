"""
LiquidacionesEdificacionesOrchestrator — fachada asíncrona ligera para controladores.

Solo delega a LiquidacionesEdificacionesFlujo. Sin lógica de negocio aquí.
"""
from injector import inject
from ninja.errors import HttpError

from ..flujos.liquidacion_edificaciones_flujo import LiquidacionesEdificacionesFlujo
from ...schemas import (
    LiquidacionEdificacionesResult,
    NuevaRevisionFormularioResult,
    RevisionVigenteResult,
    LiquidacionEdificacionesPaginatedResult,
    CotizacionQuoteData,
    ProyectistaInlineData,
    ContactoInlineData,
    DelegadosVigentesResult,
    EspecialidadBasicaResult,
)
from ...schemas_proyecto import ProyectoInlineData


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
        proyecto_public_id: str | None,
        municipalidad_id: str,
        tipo_tramite: str,
        valor_proyecto: float,
        expediente: str | None,
        valor_base_calculo: float | None,
        observacion: str | None,
        revisiones_ids: list[str],
        # Fase 6: tarifas_ids es ahora requerido — auto-selección eliminada
        tarifas_ids: list[str],
        proyectistas_inline: list[ProyectistaInlineData] | None = None,
        proyectistas_ids: list[str] | None = None,
        # NOTE: delegados_ids fue eliminado de crear_primera_revision (Fase 4).
        # Los delegados se manejarán en un endpoint POST posterior separate.
        contactos_inline: list[ContactoInlineData] | None = None,
        proyecto_inline: ProyectoInlineData | None = None,
    ) -> LiquidacionEdificacionesResult:
        """Crear primera revisión — delega a flujo."""
        # XOR validation: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente
        has_public_id = proyecto_public_id is not None and proyecto_public_id != ""
        has_inline = proyecto_inline is not None

        if has_public_id and has_inline:
            raise HttpError(400, "No se puede enviar ambos proyecto_public_id y proyecto_inline. Solo uno debe estar presente.")
        if not has_public_id and not has_inline:
            raise HttpError(400, "Debe enviarse proyecto_public_id o proyecto_inline. Uno de los dos es requerido.")

        return await self.flujo._proceso_primera_revision(
            proyecto_public_id=proyecto_public_id if has_public_id else None,
            municipalidad_id=municipalidad_id,
            tipo_tramite=tipo_tramite,
            valor_proyecto=valor_proyecto,
            expediente=expediente,
            valor_base_calculo=valor_base_calculo,
            observacion=observacion,
            revisiones_ids=revisiones_ids,
            proyectistas_inline=proyectistas_inline,
            proyectistas_ids=proyectistas_ids,
            # NOTE: delegados_ids eliminado (Fase 4)
            contactos_inline=contactos_inline,
            proyecto_inline=proyecto_inline,
            tarifas_ids=tarifas_ids,
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
        tarifas_ids: list[str] | None = None,
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
            tarifas_ids=tarifas_ids,
        )

    async def listar_liquidaciones(
        self,
        page: int,
        page_size: int,
        proyecto_public_id: str | None = None,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas — delega a flujo."""
        return await self.flujo.listar_liquidaciones_paginado(page=page, page_size=page_size, proyecto_public_id=proyecto_public_id)

    async def obtener_liquidacion_por_id(
        self,
        liquidacion_id: str,
    ) -> LiquidacionEdificacionesResult:
        """Obtiene una liquidación de edificación por ID — delega a flujo."""
        return await self.flujo._proceso_obtener_liquidacion_edificacion_detalle(liquidacion_id)

    async def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str | None = None,
    ) -> list[RevisionVigenteResult]:
        """
        Obtiene las revisiones vigentes para mostrar en formulario.

        Si tipo_tramite y tramite_accion son provistos, filtra usando ReglaTarifaEdificacion.

        Args:
            tipo_tramite: Tipo de trámite de edificación (opcional).
            tramite_accion: Acción de trámite: PRIMERA_REVISION o REVISION (opcional).

        Retorna lista tipada de RevisionVigenteResult.
        """
        return await self.flujo.obtener_revisiones_vigentes(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )

    async def cotizar_primera_revision(
        self,
        tipo_tramite: str,
        valor_proyecto: float,
        valor_base_calculo: float,
        # Fase 6: tarifas_ids es ahora requerido — auto-selección eliminada
        tarifas_ids: list[str],
    ) -> CotizacionQuoteData:
        """Cotizar primera revisión (sin guardar en BD) — delega a flujo."""
        return await self.flujo._proceso_cotizar_primera_revision(
            tipo_tramite=tipo_tramite,
            valor_proyecto=valor_proyecto,
            valor_base_calculo=valor_base_calculo,
            tarifas_ids=tarifas_ids,
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
            revision_id: UUID opcional de TarifaLiquidacionBase para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas). Default: Edificaciones
        """
        return await self.flujo._proceso_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            revision_id=revision_id,
            categoria=categoria,
        )

    async def obtener_especialidades_vigentes(self) -> list[EspecialidadBasicaResult]:
        """
        Obtiene las especialidades vigentes del grupo EspecialidadesLiquidacion.

        Retorna lista tipada de EspecialidadBasicaResult.
        """
        return await self.flujo._proceso_especialidades_vigentes()
