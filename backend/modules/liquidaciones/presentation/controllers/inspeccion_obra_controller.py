"""
InspeccionObraController — controlador HTTP ligero para Inspección de Obra.

Solo delega a InspeccionObraOrchestrator y retorna vía InspeccionObraPresenter.
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
from modules.liquidaciones.domain.services.orchestrators.inspeccion_obra_orchestrator import (
    InspeccionObraOrchestrator,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionesGeneralOrchestrator,
)
from modules.liquidaciones.domain.schemas_proyecto import (
    EntidadInlineData as DomainEntidadInlineData,
    ProyectoInlineData as DomainProyectoInlineData,
)
from modules.liquidaciones.presentation.schemas_especialidades import (
    CotizarLiquidacionInspeccionObraWrapperIn,
    CotizacionVisitasQuoteOut,
    TarifasVigentesVisitasOut,
)
from modules.liquidaciones.presentation.schemas.inspeccion_obra_schemas import (
    CrearLiquidacionInspeccionObraWrapperIn,
    LiquidacionInspeccionObraOut,
    LiquidacionIOListItemOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionGeneralListItemOut,
)
from modules.liquidaciones.domain.constants import TramiteAccion
from modules.liquidaciones.presentation.presenters.inspeccion_obra_presenter import InspeccionObraPresenter


@api_controller(
    "/liquidaciones/inspeccion-obra",
    tags=["Liquidaciones - Inspección de Obra"],
    permissions=[AllowAny],
)
class InspeccionObraController:
    """
    Controlador para Inspección Municipal de Obra.

    Endpoints:
    - GET /: Listar liquidaciones de Inspección de Obra con paginación
    - POST /primera-revision: Crear primera revisión de Inspección de Obra
    - POST /cotizar/primera-revision: Cotizar primera revisión sin guardar en BD
    """

    @inject
    def __init__(
        self,
        orchestrator: InspeccionObraOrchestrator,
        general_orchestrator: LiquidacionesGeneralOrchestrator,
    ):
        self.orchestrator = orchestrator
        self.general_orchestrator = general_orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionIOListItemOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        proyecto_public_id: str = Query(None, description="Filtrar por ID público del proyecto (ej. PROY-2026-00001)"),
    ):
        """
        Listar liquidaciones de Inspección de Obra con paginación.

        Retorna una colección/página de elementos con información básica.
        """
        result = await self.general_orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            tipo_liquidacion="INSPECCION_OBRA",
        )

        items_out = InspeccionObraPresenter.present_list(result.items)

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/primera-revision", response={200: ApiResponse[LiquidacionIOListItemOut]}, auth=None)
    async def crear_inspeccion_obra(
        self,
        payload: CrearLiquidacionInspeccionObraWrapperIn,
    ):
        """
        Crear Inspección de Obra basada en una liquidación previa.

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones (delegadas al orchestrator):
        - liquidacion_previa_id: requerido, debe existir.
        - tarifas_ids: exactamente 1 elemento si se proporciona.
        - categoria: no puede estar vacía.

        Phase 1: proyecto_public_id, proyecto_inline y municipalidad_id se ignoran
        porque se derivan de la liquidación previa (Phase 2+).
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

        # Parseo de proyectistas inline desde el payload
        from modules.liquidaciones.domain.schemas import ProyectistaInlineData
        proyectistas_inline = [
            ProyectistaInlineData(
                cip=p.cip,
                especialidad_id=p.especialidad_id,
                descripcion=p.descripcion,
            )
            for p in data.proyectistas
        ] if data.proyectistas else None

        result, calculo_visitas = await self.orchestrator.crear_primera_revision(
            liquidacion_previa_id=str(data.liquidacion_previa_id),
            proyecto_public_id=data.proyecto_public_id,
            municipalidad_id=str(data.municipalidad_id) if data.municipalidad_id else None,
            cantidad_visitas=data.cantidad_visitas,
            categoria=data.categoria,
            expediente=data.expediente,
            observacion=data.observacion,
            proyecto_inline=proyecto_inline,
            tarifas_ids=tarifas_ids,
            proyectistas_inline=proyectistas_inline,
            inspectores_ids=[str(iid) for iid in data.inspectores_ids] if data.inspectores_ids else None,
        )
        # Fetch complete record with all relations for post-create PDF
        list_item = await self.general_orchestrator.obtener_liquidacion_list_item_por_id(
            str(result.liquidacion_id)
        )
        return success_response(
            InspeccionObraPresenter.present_list_item(list_item)
        )

    @route.post("/cotizar/primera-revision", response={200: ApiResponse[CotizacionVisitasQuoteOut]}, auth=None)
    async def cotizar_primera_revision(
        self,
        payload: CotizarLiquidacionInspeccionObraWrapperIn,
    ):
        """
        Cotizar primera revisión de Inspección de Obra sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - cantidad_visitas: Cantidad de visitas de inspección
        - categoria: Categoría de inspección (A, B, C, etc.)
        - tarifas_ids: IDs de tarifas a usar (exactamente 1 elemento si se proporciona)
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.cotizar_primera_revision(
            cantidad_visitas=liquidacion_data.cantidad_visitas,
            categoria=liquidacion_data.categoria,
            tarifas_ids=[str(tid) for tid in liquidacion_data.tarifas_ids] if liquidacion_data.tarifas_ids else None,
        )
        return success_response(InspeccionObraPresenter.present_cotizacion(result))

    @route.get("/tarifas-vigentes", response={200: ApiResponse[TarifasVigentesVisitasOut]}, auth=None)
    async def obtener_tarifas_vigentes(
        self,
        tramite_accion: str = Query(
            TramiteAccion.PRIMERA_REVISION,
            description="Acción de trámite: PRIMERA_REVISION o REVISION (opcional, default PRIMERA_REVISION)",
        ),
        categoria: str | None = Query(
            None,
            description="Filtrar por categoría de inspección: CATEGORIA_A, CATEGORIA_B o CATEGORIA_C (opcional)",
        ),
    ):
        """
        Obtiene las tarifas vigentes de Inspección de Obra para selección en formulario.

        Retorna lista de tarifas de inspección con: tarifa_id (para usar en tarifas_ids),
        detalle_id, costo_por_visita, visitas_minimas, categoria, habilitada.

        Si se provee categoria, filtra las tarifas por esa categoría.
        Si no se provee, retorna tarifas de todas las categorías.
        """
        result = await self.orchestrator.obtener_tarifas_vigentes(
            tramite_accion=tramite_accion,
            categoria=categoria,
        )
        return success_response({'tarifas': result})

    @route.get("/buscar-previas", response={200: ApiResponse[PaginatedData[LiquidacionGeneralListItemOut]]}, auth=None)
    async def buscar_liquidaciones_previas(
        self,
        numero_documento: str = Query(..., description="DNI o RUC de la entidad asociada al proyecto"),
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Buscar liquidaciones previas de Inspección de Obra por documento de entidad.

        Retorna liquidaciones generales (EDIFICACION, HABILITACION_URBANA) filtradas por
        DNI/RUC de la entidad del proyecto, con paginación.

        Estas liquidaciones previas proporcionan datos comunes (proyecto, municipalidad)
        para crear nuevas Inspecciones de Obra (primera revisión).

        NOTE: Retorna LiquidacionGeneralListItemOut (estructura plana común a todos los tipos).
        El presenter InspeccionObraPresenter.present_list_item usa esta estructura general.
        """
        # Buscar liquidaciones generales de tipos base (EDIFICACION, HABILITACION_URBANA)
        # que pueden servir como previa para IO
        result = await self.general_orchestrator.buscar_liquidaciones_por_documento_entidad(
            numero_documento=numero_documento,
            tipos_liquidacion=["EDIFICACION", "HABILITACION_URBANA"],
            page=page,
            page_size=page_size,
        )

        # Transformar los LiquidacionGeneralListItem a LiquidacionGeneralListItemOut
        # usando el presenter de IO (que ahora retorna la estructura general)
        items_out = []
        for item in result.items:
            items_out.append(InspeccionObraPresenter.present_list_item(item))

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/{liquidacion_id}", response={200: ApiResponse[LiquidacionGeneralListItemOut]}, auth=None)
    async def obtener_detalle_liquidacion(
        self,
        liquidacion_id: str,
    ):
        """
        Obtener detalle de una liquidación de Inspección de Obra por ID.

        Retorna un objeto LiquidacionGeneralListItemOut con todos los campos: proyecto,
        municipalidad, valores, revisiones, proyectistas, delegados, contactos.
        """
        result = await self.general_orchestrator.obtener_liquidacion_list_item_por_id(liquidacion_id)
        return success_response(InspeccionObraPresenter.present_list_item(result))
