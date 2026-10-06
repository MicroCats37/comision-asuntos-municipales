"""
LiquidacionMecanicaSuelosController — Single unified HTTP controller for Mecánica de Suelos.

NO business logic. Only parses input, calls orchestrator, maps via presenter.
"""
import uuid
from datetime import date
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.domain.services.core.auth.auth_core_service import (
    AuthCoreService,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosInput,
    LiquidacionMecanicaSuelosOutput,
    LiquidacionMecanicaSuelosRelacionadaInput,
    LiquidacionMecanicaSuelosNuevaRevisionInput,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_mecanica_suelos_orchestrator import (
    LiquidacionMecanicaSuelosOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_tipo.liquidacion_por_metro_cuadrado_presenter import (
    LiquidacionPorMetroCuadradoPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_mecanica_suelos_presenter import (
    LiquidacionMecanicaSuelosPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    TarifasVigentesPorMetroCuadradoOutputSchema,
    CotizarPorMetroCuadradoInputSchema,
    CotizarPorMetroCuadradoOutputSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_m2_schemas import (
    LiquidacionPatchM2In,
    LiquidacionPatchM2WrapperIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
    CotizarEdicionM2WrapperIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.m2_edge_schemas import (
    M2EdgeIn,
)


@api_controller("/liquidaciones/mecanica-suelos", tags=["Mecánica de Suelos"], permissions=[AllowAny])
class LiquidacionMecanicaSuelosController:
    """
    Unified controller for Mecánica de Suelos endpoints.
    """

    @inject
    def __init__(
        self,
        cotizar_orchestrator: LiquidacionMecanicaSuelosOrchestrator,
        m2_presenter: LiquidacionPorMetroCuadradoPresenter,
        presenter: LiquidacionMecanicaSuelosPresenter,
        auth_core_service: AuthCoreService,
    ):
        self.cotizar_orchestrator = cotizar_orchestrator
        self.m2_presenter = m2_presenter
        self.presenter = presenter
        self.auth_core_service = auth_core_service

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[TarifasVigentesPorMetroCuadradoOutputSchema]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tariff and derecho for Mecánica de Suelos.
        """
        tarifa, derecho = self.cotizar_orchestrator.obtener_tarifas_vigentes_proceso()

        result = self.m2_presenter.present_tarifas_vigentes(tarifa=tarifa, derecho=derecho)
        return success_response(result)

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionMecanicaSuelosOutput]]},
        auth=None,
    )
    def list_liquidaciones(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1, le=100),
        entidad_id: uuid.UUID = Query(default=None, description="Filter by municipalidad ID"),
        propietario: str = Query(default=None, description="Filter by propietario name (icontains)"),
        fecha_desde: date = Query(default=None, description="Filter by fecha_registro >= date"),
        fecha_hasta: date = Query(default=None, description="Filter by fecha_registro <= date"),
        numero: int = Query(default=None, description="Filter by mecanica_suelos numero (exact)"),
        razon_social: str = Query(default=None, description="Filter by entidad razon_social (icontains)"),
        creado_por: str = Query(default=None, description="Filter by usuario_creador username (icontains)"),
        numero_revisiones: int = Query(default=None, description="Filter by numero_revision (exact)"),
        direccion: str = Query(default=None, description="Filter by proyecto direccion (icontains)"),
    ):
        """
        Returns a paginated list of Mecánica de Suelos liquidaciones with optional filters.
        """
        liquidaciones, total = self.cotizar_orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            municipalidad_id=entidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creado_por,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revisiones,
            direccion=direccion,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.get(
        "/{uuid:liquidacion_id}",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
        auth=None,
    )
    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single Mecánica de Suelos liquidacion by UUID.
        """
        liquidacion = self.cotizar_orchestrator.obtener_liquidacion(liquidacion_id)
        result = self.presenter.present_detalle(liquidacion)
        return success_response(result)

    @route.patch(
        "/{uuid:liquidacion_id}",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def actualizar_calculo(
        self,
        liquidacion_id: uuid.UUID,
        data: LiquidacionPatchM2WrapperIn,
    ):
        """
        PATCH recalculation of M2 calculation inputs.

        Supports two input formats:
        1. Wrapper (recommended): { liquidacion_general: {...}, liquidacion_tipo: {...} }
        2. Flat (legacy): { area_solicitada: ..., tarifa_m2_id: ... }

        Both general and tipo fields can be updated in one call.
        Solo editable cuando estado == PENDIENTE. PAGADA bloquea toda la edición.
        """
        # Extract wrapper data if present
        liquidacion_general = data.liquidacion_general.model_dump(exclude_none=True) if data.liquidacion_general else None
        liquidacion_tipo = data.liquidacion_tipo.model_dump(exclude_none=True) if data.liquidacion_tipo else None

        result = self.cotizar_orchestrator.recalcular_m2(
            liquidacion_id=liquidacion_id,
            area_solicitada=data.area_solicitada,
            tarifa_m2_id=data.tarifa_m2_id,
            liquidacion_general=liquidacion_general,
            liquidacion_tipo=liquidacion_tipo,
        )
        output = self.presenter.present_detalle(result)
        return success_response(output, message="Cálculo de mecánica de suelos actualizado correctamente.")

    @route.post(
        "/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionMecanicaSuelosInput):
        """
        Crea la Mecánica de Suelos integrando General y M2.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.cotizar_orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación de mecánica de suelos creada correctamente.")

    @route.post(
        "/nueva-revision",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def crear_nueva_revision(self, request, payload: LiquidacionMecanicaSuelosNuevaRevisionInput):
        """
        Crea una nueva revisión (3 o 5) para una Mecánica de Suelos existente.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.cotizar_orchestrator.crear_nueva_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
            liquidacion_previa_id=payload.liquidacion_previa_id,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Nueva revisión de mecánica de suelos creada correctamente.")

    @route.post(
        "/relacionada",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def crear_relacionada(self, request, payload: LiquidacionMecanicaSuelosRelacionadaInput):
        """
        Crea una liquidación relacionada a una existente con numero_revision=1.

        A diferencia de /nueva-revision que crea revisiones 3 o 5, esta endpoint
        crea una nueva liquidación con revision 1 que está relacionada a la
        liquidación previa vía Grupo/Miembro.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.cotizar_orchestrator.crear_relacionada_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
            liquidacion_previa_id=payload.liquidacion_previa_id,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación relacionada de mecánica de suelos creada correctamente.")

    @route.post(
        "/cotizar",
        response={200: ApiResponse[CotizarPorMetroCuadradoOutputSchema]},
        auth=None,
    )
    def cotizar(self, payload: CotizarPorMetroCuadradoInputSchema):
        """
        Calculates a quote for Mecánica de Suelos liquidacion.
        """
        le = payload.liquidacion_especifica
        area_solicitada = le.datos.area_solicitada
        tarifa_m2_id = le.tarifa.tarifa_m2_id

        result = self.cotizar_orchestrator.cotizar_proceso(
            area_solicitada=area_solicitada,
            tarifa_m2_id=str(tarifa_m2_id),
        )

        return success_response(self.m2_presenter.present_cotizacion(result))

    @route.post(
        "/{uuid:liquidacion_id}/cotizar-edicion",
        response={200: ApiResponse[CotizarPorMetroCuadradoOutputSchema]},
    )
    def cotizar_edicion(self, liquidacion_id: uuid.UUID, payload: CotizarEdicionM2WrapperIn):
        """
        Read-only quote preview for editing an existing Mecánica de Suelos liquidacion.

        Uses historical financial values from the existing liquidacion's fecha_registro.
        Does NOT persist any changes.
        """
        result = self.cotizar_orchestrator.cotizar_edicion_proceso(
            liquidacion_id=liquidacion_id,
            payload_in=payload,
        )
        return success_response(self.m2_presenter.present_cotizacion(result))

    @route.post(
        "/edge",
        response={200: ApiResponse[LiquidacionMecanicaSuelosOutput]},
    )
    def crear_edge(self, request, payload: M2EdgeIn):
        """
        Create an edge (manual) M2 liquidacion for Mecánica de Suelos.

        No tarifas, no costo_por_m2, no derecho — the backend calculates IGV and total
        from subtotal_manual and persists with modo_calculo=MANUAL.
        modo_calculo is set to MANUAL.
        """
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)

        domain_result = self.cotizar_orchestrator.crear_edge_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result, message="Liquidación de mecánica de suelos (edge) creada correctamente.")
