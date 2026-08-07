"""
LiquidacionInspeccionObraController — Single unified HTTP controller for Inspeccion Obra.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraInput,
    LiquidacionInspeccionObraOutput,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_inspeccion_obra_orchestrator import (
    LiquidacionInspeccionObraOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_inspeccion_obra_presenter import (
    LiquidacionInspeccionObraPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_tipo.liquidacion_por_categoria_visitas_presenter import (
    LiquidacionPorCategoriaVisitasPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    TarifasVigentesPorCategoriaVisitasOutputSchema,
    CotizarPorCategoriaVisitasInputSchema,
    CotizarPorCategoriaVisitasOutputSchema,
)

@api_controller("/liquidaciones/inspeccion-obra", tags=["Inspección de Obra"], permissions=[AllowAny])
class LiquidacionInspeccionObraController:
    """
    Unified controller for Inspeccion Obra endpoints.
    """

    @inject
    def __init__(
        self,
        general_core_service: LiquidacionGeneralCoreService,
        visitas_core_service: LiquidacionPorCategoriaVisitasCoreService,
        orchestrator: LiquidacionInspeccionObraOrchestrator,
        visitas_presenter: LiquidacionPorCategoriaVisitasPresenter,
        presenter: LiquidacionInspeccionObraPresenter,
    ):
        self.general_core_service = general_core_service
        self.visitas_core_service = visitas_core_service
        self.orchestrator = orchestrator
        self.visitas_presenter = visitas_presenter
        self.presenter = presenter

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[TarifasVigentesPorCategoriaVisitasOutputSchema]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tariffs for Inspeccion Obra (Visitas).
        """
        uit_vigente = self.general_core_service.get_uit_vigente()
        if not uit_vigente:
            return ApiResponse(success=False, error="No hay UIT vigente configurada.")

        tarifas = self.visitas_core_service.get_tarifas_vigentes()
        result = self.visitas_presenter.present_tarifas_vigentes(tarifas=tarifas, uit_vigente=uit_vigente)
        return success_response(result)

    @route.post(
        "/cotizar",
        response={200: ApiResponse[CotizarPorCategoriaVisitasOutputSchema]},
        auth=None,
    )
    def cotizar(self, payload: CotizarPorCategoriaVisitasInputSchema):
        """
        Calculates a quote for Inspeccion Obra liquidacion.
        """
        le = payload.liquidacion_especifica
        cantidad_visitas = le.datos.cantidad_visitas
        categoria = le.datos.categoria
        tarifa_visitas_id = le.tarifa.tarifa_visitas_id

        result = self.orchestrator.cotizar_proceso(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_id=str(tarifa_visitas_id),
        )

        return success_response(self.visitas_presenter.present_cotizacion(result))

    @route.post(
        "/crear-primera-revision",
        response={200: ApiResponse[LiquidacionInspeccionObraOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionInspeccionObraInput):
        """
        Crea la Inspeccion de Obra integrando General y Visitas.
        """
        usuario_id = request.user.id if request.user and request.user.is_authenticated else None
        
        domain_result = self.orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)
