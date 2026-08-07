"""
Modulo Liquidaciones — Dependency Injection wiring.
"""
from injector import Module, Binder

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


class LiquidacionesModule(Module):
    """DI module for liquidaciones package."""

    def configure(self, binder: Binder) -> None:
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
