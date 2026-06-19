"""
Módulo Usuarios — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"] o similar.
"""
from injector import Module, singleton, Binder

from .domain.services.core.auth_core_service import AuthCoreService
from .domain.services.flujos.auth_flujo import AuthFlujo
from .domain.services.orchestrators.auth_orchestrator import AuthOrchestrator


class UsuariosModule(Module):
    """
    Módulo DI para el paquete usuarios.

    Vincula:
    - AuthCoreService (operaciones síncronas)
    - AuthFlujo (flujos asíncronos, depende de AuthCoreService)
    - AuthOrchestrator (fachada ligera, depende de AuthFlujo)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Servicios de auth — ámbito singleton
        binder.bind(AuthCoreService, to=AuthCoreService, scope=singleton)
        binder.bind(AuthFlujo, to=AuthFlujo, scope=singleton)
        binder.bind(AuthOrchestrator, to=AuthOrchestrator, scope=singleton)
