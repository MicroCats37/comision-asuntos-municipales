"""
ImpactoVialController — controlador HTTP ligero para Impacto Vial.

Solo delega a ImpactoVialOrchestrator y retorna vía ImpactoVialPresenter.
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
from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
    ImpactoVialOrchestrator,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionesGeneralOrchestrator,
)
from modules.liquidaciones.domain.schemas_proyecto import (
    EntidadInlineData as DomainEntidadInlineData,
    ProyectoInlineData as DomainProyectoInlineData,
)
from modules.liquidaciones.presentation.schemas_especialidades import (
    TarifasVigentesPorcentajeOut,
)
from modules.liquidaciones.presentation.schemas.impacto_vial_schemas import (
    CrearLiquidacionImpactoVialWrapperIn,
    CotizarLiquidacionIVWrapperIn,
    LiquidacionImpactoVialOut,
    LiquidacionIVListItemOut,
    CotizacionQuoteOut,
    RevisionesVigentesOut,
)
from modules.liquidaciones.domain.constants import TramiteAccion, TipoLiquidacion
from modules.liquidaciones.presentation.presenters.impacto_vial_presenter import ImpactoVialPresenter


@api_controller(
    "/liquidaciones/impacto-vial",
    tags=["Liquidaciones - Impacto Vial"],
    permissions=[AllowAny],
)
class ImpactoVialController:
    """
    Controlador para Impacto Vial.

    Endpoints:
    - GET /: Listar liquidaciones de Impacto Vial con paginación
    - POST /nueva-liquidacion: Crear nueva liquidación (primera revisión)
    - POST /primera-revision: Crear primera revisión (alias de /nueva-liquidacion)
    - POST /cotizar/primera-revision: Cotizar primera revisión sin guardar en BD
    """

    @inject
    def __init__(
        self,
        orchestrator: ImpactoVialOrchestrator,
        general_orchestrator: LiquidacionesGeneralOrchestrator,
    ):
        self.orchestrator = orchestrator
        self.general_orchestrator = general_orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionIVListItemOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        proyecto_public_id: str = Query(None, description="Filtrar por ID público del proyecto (ej. PROY-2026-00001)"),
    ):
        """
        Listar liquidaciones de Impacto Vial con paginación.

        Retorna una colección/página de elementos con información básica.
        """
        result = await self.general_orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            tipo_liquidacion="IMPACTO_VIAL",
        )

        items_out = ImpactoVialPresenter.present_list(result.items)

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/nueva-liquidacion", response={200: ApiResponse[LiquidacionIVListItemOut]}, auth=None)
    async def crear_nueva_liquidacion(
        self,
        payload: CrearLiquidacionImpactoVialWrapperIn,
    ):
        """
        Crear nueva liquidación de Impacto Vial (primera revisión).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones (delegadas al orchestrator):
        - XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente.
        - tarifas_ids: exactamente 1 elemento si se proporciona.
        """
        data = payload.liquidacion

        # Convertir EntidadInlineIn -> EntidadInlineData (domain)
        proyecto_inline = None
        if data.proyecto_inline:
            entidad_inline = DomainEntidadInlineData(
                tipo_documento=data.proyecto_inline.entidad.tipo_documento,
                numero_documento=data.proyecto_inline.entidad.numero_documento,
                razon_social=data.proyecto_inline.entidad.razon_social,
            )
            # Convertir ProyectoInlineIn -> ProyectoInlineData (domain)
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

        result, liquidacion_porcentaje = await self.orchestrator.crear_primera_revision(
            proyecto_public_id=data.proyecto_public_id,
            municipalidad_id=str(data.municipalidad_id),
            valor_proyecto=data.valor_proyecto,
            expediente=data.expediente,
            observacion=data.observacion,
            proyecto_inline=proyecto_inline,
            tarifas_ids=tarifas_ids,
            proyectistas_inline=proyectistas_inline,
        )
        # Fetch complete record with all relations for post-create PDF
        list_item = await self.general_orchestrator.obtener_liquidacion_list_item_por_id(
            str(result.liquidacion_id)
        )
        return success_response(
            ImpactoVialPresenter.present_list_item(list_item)
        )

    @route.post("/primera-revision", response={200: ApiResponse[LiquidacionIVListItemOut]}, auth=None)
    async def crear_primera_revision(
        self,
        payload: CrearLiquidacionImpactoVialWrapperIn,
    ):
        """
        Crear primera revisión de Impacto Vial (alias de /nueva-liquidacion).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones (delegadas al orchestrator):
        - XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente.
        - tarifas_ids: exactamente 1 elemento si se proporciona.
        """
        return await self.crear_nueva_liquidacion(payload)

    @route.post("/cotizar/primera-revision", response={200: ApiResponse[CotizacionQuoteOut]}, auth=None)
    async def cotizar_primera_revision(
        self,
        payload: CotizarLiquidacionIVWrapperIn,
    ):
        """
        Cotizar primera revisión de Impacto Vial sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - liquidacion:
          - valor_proyecto: Valor del proyecto en soles para el cálculo porcentual
          - tarifas_ids: IDs de tarifas a usar (exactamente 1 elemento si se proporciona)

        Nota: tipo_liquidacion se inyecta internamente como IMPACTO_VIAL.
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.cotizar_primera_revision(
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL.value,
            valor_proyecto=liquidacion_data.valor_proyecto,
            tarifas_ids=[str(tid) for tid in liquidacion_data.tarifas_ids] if liquidacion_data.tarifas_ids else None,
        )
        return success_response(ImpactoVialPresenter.present_cotizacion_porcentaje(result))

    @route.get("/tarifas-vigentes", response={200: ApiResponse[TarifasVigentesPorcentajeOut]}, auth=None)
    async def obtener_tarifas_vigentes(
        self,
        tipo_tramite: str = Query(None, description="Tipo de trámite de edificación (opcional)"),
        tramite_accion: str = Query(
            TramiteAccion.PRIMERA_REVISION,
            description="Acción de trámite: PRIMERA_REVISION o REVISION (opcional, default PRIMERA_REVISION)",
        ),
    ):
        """
        Obtiene las tarifas vigentes de Impacto Vial para selección en formulario.

        Retorna lista de tarifas porcentuales con: tarifa_id (para usar en tarifas_ids),
        detalle_id, porcentaje_liquidacion, porcentaje_minimo_uit,
        derecho_minimo, derecho_maximo, habilitada.
        """
        result = await self.orchestrator.obtener_tarifas_vigentes(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )
        return success_response({'tarifas': result})

    @route.get("/revisiones-vigentes", response={200: ApiResponse[RevisionesVigentesOut]}, auth=None)
    async def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str = Query(None, description="Tipo de trámite de edificación (opcional)"),
        tramite_accion: str = Query(
            TramiteAccion.PRIMERA_REVISION,
            description="Acción de trámite: PRIMERA_REVISION o REVISION (opcional, default PRIMERA_REVISION)",
        ),
    ):
        """
        Obtiene las revisiones vigentes de Impacto Vial para el formulario.

        Retorna lista de revisiones con especialidades M2M, tarifa (id, porcentaje_liquidacion,
        derecho_minimo, derecho_maximo, porcentaje_minimo_uit) y si está habilitada.

        Este endpoint replica el contrato de /liquidaciones/edificaciones/revisiones-vigentes.
        """
        result = await self.orchestrator.obtener_revisiones_vigentes(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )
        return success_response({'revisiones': result})

    @route.get("/{liquidacion_id}", response={200: ApiResponse[LiquidacionIVListItemOut]}, auth=None)
    async def obtener_detalle_liquidacion(
        self,
        liquidacion_id: str,
    ):
        """
        Obtener detalle de una liquidación de Impacto Vial por ID.

        Retorna un objeto LiquidacionIVListItemOut con todos los campos: proyecto,
        municipalidad, valores, revisiones, proyectistas, delegados, contactos.
        """
        result = await self.general_orchestrator.obtener_liquidacion_list_item_por_id(liquidacion_id)
        return success_response(ImpactoVialPresenter.present_list_item(result))
