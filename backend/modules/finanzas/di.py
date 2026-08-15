"""
Módulo Finanzas — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator


class FinanzasModule(Module):
    """
    Módulo DI para el paquete finanzas.

    Vincula:
    - FinanzasCoreService — ORM queries for IGV/UIT
    - FinanzasFlujo — flujos async (envuelve el Core en sync_to_async)
    - FinanzasOrchestrator — fachada para obtener variables vigentes

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(FinanzasCoreService, to=FinanzasCoreService, scope=singleton)
        binder.bind(FinanzasFlujo, to=FinanzasFlujo, scope=singleton)
        binder.bind(FinanzasOrchestrator, to=FinanzasOrchestrator, scope=singleton)
