"""
Módulo Finanzas — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
    RHInspectorMensualListFlujo,
)
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualCotizarFlujo,
    RHDelegadoMensualCrearFlujo,
)
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.domain.services.core.rh_reparticion_estacional_core_service import (
    RHReparticionEstacionalCoreService,
)
from modules.finanzas.domain.services.flujos.rh_reparticion_estacional_flujo import (
    RHReparticionEstacionalFlujo,
)
from modules.finanzas.domain.services.orchestrators.rh_reparticion_estacional_orchestrator import (
    RHReparticionEstacionalOrchestrator,
)


class FinanzasModule(Module):
    """
    Módulo DI para el paquete finanzas.

    Vincula:
    - FinanzasCoreService - ORM queries for IGV/UIT
    - FinanzasFlujo - flujos async (envuelve el Core en sync_to_async)
    - RHInspectorMensualCotizarFlujo / RHInspectorMensualCrearFlujo - RH mensual inspector
    - RHDelegadoMensualCotizarFlujo / RHDelegadoMensualCrearFlujo - RH mensual delegado
    - FinanzasOrchestrator - fachada para obtener variables vigentes
    - RHReparticionEstacionalCoreService / RHReparticionEstacionalFlujo / RHReparticionEstacionalOrchestrator - RH reparticion estacional

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(FinanzasCoreService, to=FinanzasCoreService, scope=singleton)
        binder.bind(FinanzasFlujo, to=FinanzasFlujo, scope=singleton)
        binder.bind(RHInspectorMensualCotizarFlujo, to=RHInspectorMensualCotizarFlujo, scope=singleton)
        binder.bind(RHInspectorMensualCrearFlujo, to=RHInspectorMensualCrearFlujo, scope=singleton)
        binder.bind(RHInspectorMensualListFlujo, to=RHInspectorMensualListFlujo, scope=singleton)
        binder.bind(RHDelegadoMensualCotizarFlujo, to=RHDelegadoMensualCotizarFlujo, scope=singleton)
        binder.bind(RHDelegadoMensualCrearFlujo, to=RHDelegadoMensualCrearFlujo, scope=singleton)
        binder.bind(FinanzasOrchestrator, to=FinanzasOrchestrator, scope=singleton)
        binder.bind(RHReparticionEstacionalCoreService, to=RHReparticionEstacionalCoreService, scope=singleton)
        binder.bind(RHReparticionEstacionalFlujo, to=RHReparticionEstacionalFlujo, scope=singleton)
        binder.bind(RHReparticionEstacionalOrchestrator, to=RHReparticionEstacionalOrchestrator, scope=singleton)
