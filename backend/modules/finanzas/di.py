"""
Módulo Finanzas — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from .domain.services.finanzas_core_service import FinanzasCoreService
from .domain.services.finanzas_orchestrator import FinanzasOrchestrator


class FinanzasModule(Module):
    """
    Módulo DI para el paquete finanzas.

    Vincula:
    - FinanzasCoreService (operaciones síncronas)
    - FinanzasOrchestrator (fachada ligera, depende de CoreService)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(FinanzasCoreService, to=FinanzasCoreService, scope=singleton)
        binder.bind(FinanzasOrchestrator, to=FinanzasOrchestrator, scope=singleton)
