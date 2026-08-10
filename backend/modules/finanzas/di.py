"""
Módulo Finanzas — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator


class FinanzasModule(Module):
    """
    Módulo DI para el paquete finanzas.

    Vincula:
    - FinanzasOrchestrator — fachada para obtener variables vigentes

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(FinanzasOrchestrator, to=FinanzasOrchestrator, scope=singleton)
