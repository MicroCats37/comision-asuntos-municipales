"""
Módulo Entidades — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from .domain.services.entidades_core_service import EntidadesCoreService
from .domain.services.flujos.entidad_flujo import EntidadFlujo
from .domain.services.orchestrators.entidad_orchestrator import EntidadesOrchestrator


class EntidadesModule(Module):
    """
    Módulo DI para el paquete entidades.

    Vincula:
    - EntidadesCoreService (operaciones síncronas)
    - EntidadFlujo (flujos asíncronos, depende de CoreService)
    - EntidadesOrchestrator (fachada ligera, depende de Flujo)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(EntidadesCoreService, to=EntidadesCoreService, scope=singleton)
        binder.bind(EntidadFlujo, to=EntidadFlujo, scope=singleton)
        binder.bind(EntidadesOrchestrator, to=EntidadesOrchestrator, scope=singleton)
