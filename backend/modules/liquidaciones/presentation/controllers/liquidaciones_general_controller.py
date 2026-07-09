"""
LiquidacionesGeneralController — controlador HTTP ligero para liquidaciones generales.

Solo delega a LiquidacionesGeneralOrchestrator y retorna vía presenter.

Endpoints:
- GET /: Listar liquidaciones generales con paginación
- GET /especialidades-vigentes?tipo_liquidacion=...: Catálogo de especialidades vigentes
- GET /delegados/vigentes?municipalidad_id=&tipo_liquidacion=&revision_id=: Delegados vigentes
- GET /general/{liquidacion_id}: Obtener detalle de una liquidación por ID
- PATCH /{liquidacion_id}/delegados: Batch create/update/delete de delegados
"""
import uuid

from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from ..schemas.liquidacion_general_schemas import (
    LiquidacionGeneralOut,
    LiquidacionGeneralListItemOut,
    EspecialidadesCatalogoOut,
    DelegadosVigentesOut,
)
from ..schemas.delegados_batch_schemas import (
    LiquidacionDelegadoBatchIn,
    LiquidacionDelegadoBatchOut,
)
from ..presenters.liquidacion_general_presenter import LiquidacionGeneralPresenter
from ...domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionesGeneralOrchestrator,
)
from ...domain.services.orchestrators.delegados_batch_orchestrator import (
    DelegadosBatchOrchestrator,
)


@api_controller(
    "/liquidaciones",
    tags=["Liquidaciones General"],
    permissions=[AllowAny],
)
class LiquidacionesGeneralController:
    """
    Controlador para operaciones generales de liquidaciones.

    Provee endpoints de listado y detalle que funcionan para
    cualquier tipo de liquidación (Edificación, Habilitación Urbana,
    Mecánica de Suelos, Impacto Vial, Taludes, Inspección de Obra).

    Endpoints:
    - GET /: Listar liquidaciones con paginación
    - GET /{liquidacion_id}: Obtener detalle de una liquidación
    - PATCH /{liquidacion_id}/delegados: Batch create/update/delete de delegados
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionesGeneralOrchestrator,
        batch_orchestrator: DelegadosBatchOrchestrator,
    ):
        self.orchestrator = orchestrator
        self.batch_orchestrator = batch_orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionGeneralListItemOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Listar TODAS las liquidaciones generales con paginación.

        Retorna una colección/página de elementos con información
        básica de cualquier tipo de liquidación (Edificación,
        Habilitación Urbana, Mecánica de Suelos, Impacto Vial,
        Taludes, Inspección de Obra).

        No filtra por tipo — incluye todos los tipos.
        """
        result = await self.orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
        )

        # Transformar cada LiquidacionGeneralListItem a LiquidacionGeneralListItemOut
        items_out = LiquidacionGeneralPresenter.present_list(result.items)

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/general/{liquidacion_id}", response={200: ApiResponse[LiquidacionGeneralOut]}, auth=None)
    async def obtener_detalle_liquidacion(
        self,
        liquidacion_id: str,
    ):
        """
        Obtener detalle de una liquidación por ID.

        Retorna un objeto LiquidacionGeneralOut con todos los campos
        comunes a todos los tipos de liquidación.

        Args:
            liquidacion_id: UUID de la liquidación
        """
        result = await self.orchestrator.obtener_liquidacion_por_id(liquidacion_id)
        return success_response(LiquidacionGeneralPresenter.present(result))

    @route.get("/especialidades-vigentes", response={200: ApiResponse[EspecialidadesCatalogoOut]}, auth=None)
    async def obtener_especialidades_vigentes(
        self,
        tipo_liquidacion: str = Query(..., description="Tipo de liquidación (slug o enum, ej. habilitacion-urbana, HABILITACION_URBANA)"),
    ):
        """
        Obtiene las especialidades vigentes para un tipo de liquidación dado.

        Retorna un catálogo de especialidades activas basadas en el grupo
        EspecialidadesLiquidacion vigente para el tipo especificado.

        Tipos soportados (slugs):
        - habilitacion-urbana
        - mecanica-suelos
        - impacto-vial
        - taludes
        - inspeccion-obra
        - edificacion

        Args:
            tipo_liquidacion: Slug o valor enum del tipo de liquidación

        Returns:
            EspecialidadesCatalogoOut con lista de especialidades {id, nombre}
        """
        result = await self.orchestrator.obtener_especialidades_vigentes_por_tipo(
            tipo_liquidacion=tipo_liquidacion,
        )
        return success_response({'items': result})

    @route.get("/delegados/vigentes", response={200: ApiResponse[DelegadosVigentesOut]}, auth=None)
    async def obtener_delegados_vigentes(
        self,
        municipalidad_id: str = Query(..., description="ID de la municipalidad (UUID)"),
        tipo_liquidacion: str = Query(..., description="Tipo de liquidación (slug o enum)"),
        revision_id: str = Query(..., description="ID de la TarifaLiquidacionBase para filtrar por especialidades"),
    ):
        result = await self.orchestrator.obtener_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            tipo_liquidacion=tipo_liquidacion,
            revision_id=revision_id,
        )
        return success_response(LiquidacionGeneralPresenter.present_delegados_vigentes(result))

    @route.patch(
        "/{liquidacion_id}/delegados",
        response={200: ApiResponse[LiquidacionDelegadoBatchOut]},
        auth=None,
    )
    async def batch_delegados(
        self,
        liquidacion_id: str,
        payload: LiquidacionDelegadoBatchIn,
    ):
        """
        Batch create/update/delete de delegados de una liquidación.

        Procesa create, update y delete en una sola transacción atómica.
        Si cualquier operación falla, se hace rollback completo.

        Args:
            liquidacion_id: UUID de la liquidación objetivo.
            payload: BatchPayload con listas de create, update y delete.

        Returns:
            LiquidacionDelegadoBatchOut con resultados de cada operación.
        """
        lid = uuid.UUID(liquidacion_id)
        result = await self.batch_orchestrator.procesar_batch_delegados(
            liquidacion_id=lid,
            payload=payload,
        )
        return success_response(result)
