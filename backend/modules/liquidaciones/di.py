"""
Modulo Liquidaciones — Dependency Injection wiring.
"""
from injector import Module, Binder

from modules.liquidaciones.domain.services.core.auth.auth_core_service import (
    AuthCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_tipo.liquidacion_por_metro_cuadrado_flujo import (
    LiquidacionPorMetroCuadradoFlujo,
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
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_mecanica_suelos_orchestrator import (
    LiquidacionMecanicaSuelosOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_mecanica_suelos_presenter import (
    LiquidacionMecanicaSuelosPresenter,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_edificaciones_flujo import (
    LiquidacionEdificacionesFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_edificaciones_orchestrator import (
    LiquidacionEdificacionesOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_edificaciones_presenter import (
    LiquidacionEdificacionesPresenter,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_impacto_vial_flujo import (
    LiquidacionImpactoVialFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_impacto_vial_orchestrator import (
    LiquidacionImpactoVialOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_impacto_vial_presenter import (
    LiquidacionImpactoVialPresenter,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_taludes_flujo import (
    LiquidacionTaludesFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_taludes_orchestrator import (
    LiquidacionTaludesOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_taludes_presenter import (
    LiquidacionTaludesPresenter,
)
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.delegado_orchestrator import (
    DelegadoOrchestrator,
)
from modules.liquidaciones.presentation.presenters.delegado_presenter import (
    DelegadoPresenter,
)
from modules.liquidaciones.domain.services.core.inspector.inspector_core_service import (
    InspectorCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.inspector_orchestrator import (
    InspectorOrchestrator,
)
from modules.liquidaciones.presentation.presenters.inspector_presenter import (
    InspectorPresenter,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.tarifas_historicas_orchestrator import (
    TarifasHistoricasOrchestrator,
)
from modules.liquidaciones.domain.services.orchestrators.derechos_historicos_orchestrator import (
    DerechosHistoricosOrchestrator,
)
from modules.liquidaciones.presentation.presenters.tarifas_historicas_presenter import (
    TarifasHistoricasPresenter,
    DerechosHistoricosPresenter,
)


class LiquidacionesModule(Module):
    """DI module for liquidaciones package."""

    def configure(self, binder: Binder) -> None:
        # Core services — Auth
        binder.bind(AuthCoreService, to=AuthCoreService)

        # Core services — General
        binder.bind(LiquidacionGeneralCoreService, to=LiquidacionGeneralCoreService)

        # Core services — Tipo M2
        binder.bind(LiquidacionPorMetroCuadradoCoreService, to=LiquidacionPorMetroCuadradoCoreService)

        # Flujos — Tipo M2
        binder.bind(LiquidacionPorMetroCuadradoFlujo, to=LiquidacionPorMetroCuadradoFlujo)

        # Orchestrators — Específico
        binder.bind(LiquidacionHabilitacionUrbanaOrchestrator, to=LiquidacionHabilitacionUrbanaOrchestrator)

        # Presenters — Tipo M2
        binder.bind(LiquidacionPorMetroCuadradoPresenter, to=LiquidacionPorMetroCuadradoPresenter)

        # Presenters — Específico
        binder.bind(LiquidacionHabilitacionUrbanaPresenter, to=LiquidacionHabilitacionUrbanaPresenter)

        # Orchestrators — Mecánica de Suelos
        binder.bind(LiquidacionMecanicaSuelosOrchestrator, to=LiquidacionMecanicaSuelosOrchestrator)

        # Presenters — Mecánica de Suelos
        binder.bind(LiquidacionMecanicaSuelosPresenter, to=LiquidacionMecanicaSuelosPresenter)

        # Core services — Tipo PorcentajeObra
        binder.bind(LiquidacionPorcentajeObraCoreService, to=LiquidacionPorcentajeObraCoreService)

        # Flujos — Edificaciones
        binder.bind(LiquidacionEdificacionesFlujo, to=LiquidacionEdificacionesFlujo)

        # Orchestrators — Edificaciones
        binder.bind(LiquidacionEdificacionesOrchestrator, to=LiquidacionEdificacionesOrchestrator)

        # Presenters — Edificaciones
        binder.bind(LiquidacionEdificacionesPresenter, to=LiquidacionEdificacionesPresenter)

        # Flujos — Impacto Vial
        binder.bind(LiquidacionImpactoVialFlujo, to=LiquidacionImpactoVialFlujo)

        # Orchestrators — Impacto Vial
        binder.bind(LiquidacionImpactoVialOrchestrator, to=LiquidacionImpactoVialOrchestrator)

        # Presenters — Impacto Vial
        binder.bind(LiquidacionImpactoVialPresenter, to=LiquidacionImpactoVialPresenter)

        # Flujos — Taludes
        binder.bind(LiquidacionTaludesFlujo, to=LiquidacionTaludesFlujo)

        # Orchestrators — Taludes
        binder.bind(LiquidacionTaludesOrchestrator, to=LiquidacionTaludesOrchestrator)

        # Presenters — Taludes
        binder.bind(LiquidacionTaludesPresenter, to=LiquidacionTaludesPresenter)

        # Core — Delegado
        binder.bind(DelegadoCoreService, to=DelegadoCoreService)

        # Orchestrators — Delegado
        binder.bind(DelegadoOrchestrator, to=DelegadoOrchestrator)

        # Presenters — Delegado
        binder.bind(DelegadoPresenter, to=DelegadoPresenter)

        # Core — Inspector
        binder.bind(InspectorCoreService, to=InspectorCoreService)

        # Orchestrators — Inspector
        binder.bind(InspectorOrchestrator, to=InspectorOrchestrator)

        # Presenters — Inspector
        binder.bind(InspectorPresenter, to=InspectorPresenter)

        # Core — Tarifas Historicas
        binder.bind(TarifasHistoricasCoreService, to=TarifasHistoricasCoreService)

        # Orchestrators — Tarifas Historicas
        binder.bind(TarifasHistoricasOrchestrator, to=TarifasHistoricasOrchestrator)
        binder.bind(DerechosHistoricosOrchestrator, to=DerechosHistoricosOrchestrator)

        # Presenters — Tarifas Historicas
        binder.bind(TarifasHistoricasPresenter, to=TarifasHistoricasPresenter)
        binder.bind(DerechosHistoricosPresenter, to=DerechosHistoricosPresenter)
