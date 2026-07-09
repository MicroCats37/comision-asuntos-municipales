"""
TaludesController — controlador HTTP ligero para Taludes.

Solo delega a TaludesOrchestrator y retorna vía TaludesPresenter.
Patrón: JSON Estricto (Patrón 3) — recibe payload JSON tipado, convierte DTOs, llama orchestrator.

NO lógica de negocio, NO ORM directo, NO transacciones en controller.
NO incluye endpoints de nueva revisión.
"""

from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.orchestrators.taludes_orchestrator import (
    TaludesOrchestrator,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionesGeneralOrchestrator,
)
from modules.liquidaciones.domain.schemas_proyecto import (
    EntidadInlineData as DomainEntidadInlineData,
    ProyectoInlineData as DomainProyectoInlineData,
)
from modules.liquidaciones.presentation.schemas_especialidades import (
    CotizacionM2QuoteOut,
    TarifasVigentesM2Out,
)
from modules.liquidaciones.presentation.schemas.taludes_schemas import (
    CrearLiquidacionTaludesWrapperIn,
    CotizarLiquidacionTaludesWrapperIn,
    LiquidacionTaludesOut,
)
from modules.liquidaciones.domain.constants import TramiteAccion, TipoLiquidacion
from modules.liquidaciones.presentation.presenters.taludes_presenter import TaludesPresenter
from modules.liquidaciones.presentation.presenters.liquidacion_general_presenter import LiquidacionGeneralPresenter
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionGeneralListItemOut,
)


@api_controller(
    "/liquidaciones/taludes",
    tags=["Liquidaciones - Taludes"],
    permissions=[AllowAny],
)
class TaludesController:
    """
    Controlador para Taludes.

    Endpoints:
    - GET /: Listar liquidaciones de Taludes con paginación
    - POST /primera-revision: Crear primera revisión de Taludes
    - POST /cotizar/primera-revision: Cotizar primera revisión sin guardar en BD
    """

    @inject
    def __init__(
        self,
        orchestrator: TaludesOrchestrator,
        general_orchestrator: LiquidacionesGeneralOrchestrator,
    ):
        self.orchestrator = orchestrator
        self.general_orchestrator = general_orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionGeneralListItemOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        proyecto_public_id: str = Query(None, description="Filtrar por ID público del proyecto (ej. PROY-2026-00001)"),
    ):
        """
        Listar liquidaciones de Taludes con paginación.

        Retorna una colección/página de elementos con información básica.
        """
        result = await self.general_orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            tipo_liquidacion="TALUDES",
        )

        items_out = LiquidacionGeneralPresenter.present_list(result.items)

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/primera-revision", response={200: ApiResponse[LiquidacionTaludesOut]}, auth=None)
    async def crear_taludes(
        self,
        payload: CrearLiquidacionTaludesWrapperIn,
    ):
        """
        Crear primera revisión de Taludes.

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones (delegadas al orchestrator):
        - XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente.
        - tarifas_ids: exactamente 1 elemento si se proporciona.
        """
        data = payload.liquidacion

        # Convertir EntidadInlineIn/ProyectoInlineIn -> domain solo si viene inline
        proyecto_inline = None
        if data.proyecto_inline:
            entidad_inline = DomainEntidadInlineData(
                tipo_documento=data.proyecto_inline.entidad.tipo_documento,
                numero_documento=data.proyecto_inline.entidad.numero_documento,
                razon_social=data.proyecto_inline.entidad.razon_social,
            )
            proyecto_inline = DomainProyectoInlineData(
                denominacion=data.proyecto_inline.denominacion,
                direccion=data.proyecto_inline.direccion,
                distrito_id=data.proyecto_inline.distrito_id,
                nombre_propietario=data.proyecto_inline.nombre_propietario,
                entidad=entidad_inline,
            )

        # Convertir tarifas_ids UUIDs -> strings
        tarifas_ids = [str(tid) for tid in data.tarifas_ids] if data.tarifas_ids else None

        result, calculo_m2 = await self.orchestrator.crear_primera_revision(
            proyecto_public_id=data.proyecto_public_id,
            municipalidad_id=str(data.municipalidad_id),
            area_solicitada=data.area_solicitada,
            expediente=data.expediente,
            observacion=data.observacion,
            proyecto_inline=proyecto_inline,
            tarifas_ids=tarifas_ids,
        )
        return success_response(
            TaludesPresenter.present(result, calculo_m2)
        )

    @route.post("/cotizar/primera-revision", response={200: ApiResponse[CotizacionM2QuoteOut]}, auth=None)
    async def cotizar_primera_revision(
        self,
        payload: CotizarLiquidacionTaludesWrapperIn,
    ):
        """
        Cotizar primera revisión de Taludes sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - liquidacion:
          - area_solicitada: Área solicitada en metros cuadrados
          - tarifas_ids: IDs de tarifas a usar (exactamente 1 elemento si se proporciona)

        Nota: tipo_liquidacion se inyecta internamente como TALUDES.
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.cotizar_primera_revision(
            tipo_liquidacion=TipoLiquidacion.TALUDES.value,
            area_solicitada=liquidacion_data.area_solicitada,
            tarifas_ids=[str(tid) for tid in liquidacion_data.tarifas_ids] if liquidacion_data.tarifas_ids else None,
        )
        return success_response(TaludesPresenter.present_cotizacion(result))

    @route.get("/tarifas-vigentes", response={200: ApiResponse[TarifasVigentesM2Out]}, auth=None)
    async def obtener_tarifas_vigentes(
        self,
        tramite_accion: str = Query(
            TramiteAccion.PRIMERA_REVISION,
            description="Acción de trámite: PRIMERA_REVISION o REVISION (opcional, default PRIMERA_REVISION)",
        ),
    ):
        """
        Obtiene las tarifas vigentes de Taludes para selección en formulario.

        Retorna lista de tarifas M2 con: tarifa_id (para usar en tarifas_ids),
        detalle_id, costo_por_m2, area_minima, derecho_minimo, derecho_maximo, habilitada.
        """
        result = await self.orchestrator.obtener_tarifas_vigentes(tramite_accion=tramite_accion)
        return success_response({'tarifas': result})
