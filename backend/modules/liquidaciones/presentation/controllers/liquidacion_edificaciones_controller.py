"""
LiquidacionesEdificacionesController — controladores HTTP ligeros.

Solo delega a LiquidacionesEdificacionesOrchestrator y retorna vía presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query
from typing import Dict, Any

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from ..schemas.liquidacion_edificaciones_schemas import (
    PrimeraRevisionLiquidacionWrapperIn,
    PrimeraRevisionLiquidacionIn,
    NuevaRevisionLiquidacionIn,
    LiquidacionSnapshotOut,
    NuevaRevisionFormularioOut,
    RevisionesVigentesOut,
    LiquidacionEdificacionesListItemOut,
    LiquidacionSnapshotListItemOut,
    CotizacionPrimeraRevisionWrapperIn,
    CotizacionNuevaRevisionIn,
    CotizacionQuoteOut,
)
from ..presenters.liquidacion_edificaciones_presenter import LiquidacionEdificacionesPresenter
from ...domain.services.orchestrators.liquidacion_edificaciones_orchestrator import LiquidacionesEdificacionesOrchestrator


@api_controller("/liquidaciones/edificaciones", tags=["Liquidaciones Edificaciones"], permissions=[AllowAny])
class LiquidacionEdificacionesController:
    """
    Controlador para Liquidaciones Edificaciones.

    Endpoints:
    - GET /: Listar liquidaciones con paginación
    - POST /primera-revision: Crear primera revisión
    - GET /nueva-revision/formulario: Preparar formulario para nueva revisión
    - POST /nueva-revision: Crear nueva revisión
    - GET /{liquidacion_id}: Obtener detalle/snapshot de liquidación
    """

    @inject
    def __init__(self, orchestrator: LiquidacionesEdificacionesOrchestrator):
        self.orchestrator = orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionEdificacionesListItemOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Listar liquidaciones de edificaciones con paginación.

        Retorna para cada item: id, numero_revision, estado,
        valor_proyecto, proyecto_public_id, proyecto_denominacion,
        fecha_registro, total.
        """
        result = await self.orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
        )

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=result.items,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/nueva-liquidacion", response={200: ApiResponse[LiquidacionSnapshotOut]}, auth=None)
    async def crear_nueva_liquidacion(self, payload: PrimeraRevisionLiquidacionWrapperIn):
        """
        Crear nueva liquidación de edificaciones (primera revisión).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones:
        - El proyecto debe existir
        - La municipalidad debe existir
        - No debe existir ya una primera revisión para ese proyecto
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.crear_primera_revision(
            proyecto_public_id=liquidacion_data.proyecto_public_id,
            municipalidad_id=str(liquidacion_data.municipalidad_id),
            tipo_tramite=liquidacion_data.tipo_tramite,
            valor_proyecto=liquidacion_data.valor_proyecto,
            observacion=liquidacion_data.observacion,
            revisiones_ids=liquidacion_data.revisiones_ids,
            proyectistas_ids=[str(pid) for pid in liquidacion_data.proyectistas_ids],
        )
        return success_response(LiquidacionEdificacionesPresenter.present_snapshot(result))

    @route.post("/primera-revision", response={200: ApiResponse[LiquidacionSnapshotOut]}, auth=None)
    async def crear_primera_revision(self, payload: PrimeraRevisionLiquidacionWrapperIn):
        """
        Crear primera revisión de liquidación de edificaciones (alias de /nueva-liquidacion).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones:
        - El proyecto debe existir
        - La municipalidad debe existir
        - No debe existir ya una primera revisión para ese proyecto
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        """
        return await self.crear_nueva_liquidacion(payload)

    @route.post("/cotizar/primera-revision", response={200: ApiResponse[CotizacionQuoteOut]}, auth=None)
    async def cotizar_primera_revision(self, payload: CotizacionPrimeraRevisionWrapperIn):
        """
        Cotizar primera revisión sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - proyecto_public_id: ID público del proyecto
        - valor_proyecto: Valor del proyecto

        Usa selección por defecto de revisiones vigentes.
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.cotizar_primera_revision(
            proyecto_public_id=liquidacion_data.proyecto_public_id,
            valor_proyecto=liquidacion_data.valor_proyecto,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_cotizacion(result))

    @route.post("/cotizar/nueva-revision", response={200: ApiResponse[CotizacionQuoteOut]}, auth=None)
    async def cotizar_nueva_revision(self, payload: CotizacionNuevaRevisionIn):
        """
        Cotizar nueva revisión sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - liquidacion_previa_id: ID de la liquidación previa
        - revisiones_ids: IDs de revisiones (NO puede estar vacío — 422 si se envía vacío)

        No requiere valor_proyecto; se obtiene de la liquidación previa.
        """
        result = await self.orchestrator.cotizar_nueva_revision(
            liquidacion_previa_id=str(payload.liquidacion_previa_id),
            revisiones_ids=payload.revisiones_ids,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_cotizacion(result))

    @route.get("/nueva-revision/formulario", response={200: ApiResponse[NuevaRevisionFormularioOut]}, auth=None)
    async def preparar_nueva_revision(
        self,
        liquidacion_previa_id: str = Query(..., description="ID de la liquidación previa (UUID)"),
    ):
        """
        Preparar formulario para nueva revisión.

        Devuelve:
        - Siguiente número de revisión
        - Si cobrará o no
        - Datos del proyecto
        - Revisiones vigentes disponibles
        """
        result = await self.orchestrator.preparar_nueva_revision(
            liquidacion_previa_id=liquidacion_previa_id,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_formulario(result))

    @route.post("/nueva-revision", response={200: ApiResponse[LiquidacionSnapshotOut]}, auth=None)
    async def crear_nueva_revision(self, payload: NuevaRevisionLiquidacionIn):
        """
        Crear nueva revisión de liquidación de edificaciones.

        Validaciones:
        - La liquidación previa debe existir y ser de edificaciones
        - El número de revisión no puede exceder 7
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        - proyectistas_ids es opcional; si se omite o está vacío, se heredan de la liquidación previa
        """
        result = await self.orchestrator.crear_nueva_revision(
            liquidacion_previa_id=str(payload.liquidacion_previa_id),
            observacion=payload.observacion,
            revisiones_ids=[str(rid) for rid in payload.revisiones_ids],
            proyectistas_ids=[str(pid) for pid in payload.proyectistas_ids] if payload.proyectistas_ids else None,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_snapshot(result))

    @route.get("/revisiones-vigentes", response={200: ApiResponse[RevisionesVigentesOut]}, auth=None)
    async def obtener_revisiones_vigentes(self):
        """
        Obtiene todas las revisiones/especialidades vigentes para mostrar en formulario.

        Retorna lista de revisiones con especialidad, tarifa (derecho_minimo,
        derecho_maximo, porcentaje_minimo_uit) y si está habilitada.
        """
        result = await self.orchestrator.obtener_revisiones_vigentes()
        return success_response({'revisiones': result})

    @route.get("/snapshots", response={200: ApiResponse[PaginatedData[LiquidacionSnapshotListItemOut]]}, auth=None)
    async def listar_snapshots(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=50, description="Elementos por página"),
    ):
        """
        Listar snapshots completos de liquidaciones con paginación.

        Retorna para cada item: liquidacion_id, numero_liquidacion, estado,
        fecha_registro, observacion, proyecto (con entidad),
        edificaciones (con revisiones, tarifas y proyectistas), totales.
        """
        items, total = await self.orchestrator.listar_snapshots(
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return success_response(PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/{liquidacion_id}", response={200: ApiResponse[Dict[Any, Any]]}, auth=None)
    async def obtener_liquidacion(
        self,
        liquidacion_id: str,
    ):
        """
        Obtener detalle/snapshot de una liquidación de edificaciones.

        Retorna el JSON completo almacenado en LiquidacionSnapshot.data,
        sin proyección — incluye todos los campos guardados (liquidacion,
        edificaciones, totales, _metadata y cualquier campo adicional).
        """
        result = await self.orchestrator.obtener_liquidacion(
            liquidacion_id=liquidacion_id,
        )
        return success_response(result)