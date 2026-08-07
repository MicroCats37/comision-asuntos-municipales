"""
LiquidacionHabilitacionUrbanaController — Single unified HTTP controller for Habilitacion Urbana.

NO business logic. Only parses input, calls orchestrator, maps via presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaInput,
    LiquidacionHabilitacionUrbanaOutput,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_habilitacion_urbana_orchestrator import (
    LiquidacionHabilitacionUrbanaOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_tipo.liquidacion_por_metro_cuadrado_presenter import (
    LiquidacionPorMetroCuadradoPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_habilitacion_urbana_presenter import (
    LiquidacionHabilitacionUrbanaPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    TarifasVigentesPorMetroCuadradoOutputSchema,
    CotizarPorMetroCuadradoInputSchema,
    CotizarPorMetroCuadradoOutputSchema,
)


@api_controller("/liquidaciones/habilitacion-urbana", tags=["Habilitación Urbana"], permissions=[AllowAny])
class LiquidacionHabilitacionUrbanaController:
    """
    Unified controller for Habilitacion Urbana endpoints.
    """

    @inject
    def __init__(
        self,
        m2_core_service: LiquidacionPorMetroCuadradoCoreService,
        cotizar_orchestrator: LiquidacionHabilitacionUrbanaOrchestrator,
        m2_presenter: LiquidacionPorMetroCuadradoPresenter,
        presenter: LiquidacionHabilitacionUrbanaPresenter,
    ):
        self.m2_core_service = m2_core_service
        self.cotizar_orchestrator = cotizar_orchestrator
        self.m2_presenter = m2_presenter
        self.presenter = presenter

    @route.get(
        "/tarifas/vigentes",
        response={200: ApiResponse[TarifasVigentesPorMetroCuadradoOutputSchema]},
        auth=None,
    )
    def get_tarifas_vigentes(self):
        """
        Get the currently active tariff and derecho for Habilitacion Urbana.
        """
        tarifa = self.m2_core_service.get_tarifa_m2_vigente(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        )
        derecho = self.m2_core_service.get_derecho_minimo_m2_vigente()

        result = self.m2_presenter.present_tarifas_vigentes(tarifa=tarifa, derecho=derecho)
        return success_response(result)

    @route.post(
        "/nueva-liquidacion/primera-revision",
        response={200: ApiResponse[LiquidacionHabilitacionUrbanaOutput]},
    )
    def crear_primera_revision(self, request, payload: LiquidacionHabilitacionUrbanaInput):
        """
        Crea la Habilitacion Urbana integrando General y M2.
        """
        # Extract user id from JWT (ninja_jwt sets request.user on success).
        usuario_id = request.user.id if request.user and request.user.is_authenticated else None

        domain_result = self.cotizar_orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )

        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)

    @route.post(
        "/cotizar",
        response={200: ApiResponse[CotizarPorMetroCuadradoOutputSchema]},
        auth=None,
    )
    def cotizar(self, payload: CotizarPorMetroCuadradoInputSchema):
        """
        Calculates a quote for Habilitacion Urbana liquidacion.
        """
        le = payload.liquidacion_especifica
        area_solicitada = le.datos.area_solicitada
        tarifa_m2_id = le.tarifa.tarifa_m2_id

        result = self.cotizar_orchestrator.cotizar_proceso(
            area_solicitada=area_solicitada,
            tarifa_m2_id=str(tarifa_m2_id),
        )

        return success_response(self.m2_presenter.present_cotizacion(result))
