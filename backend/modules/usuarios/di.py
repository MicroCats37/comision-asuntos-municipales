"""
Módulo Usuarios — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"] o similar.
"""
import os

from django.conf import settings
from injector import Module, singleton, Binder

from .domain.services.core.auth_core_service import AuthCoreService
from .domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService
from .domain.services.flujos.auth_flujo import AuthFlujo
from .domain.services.flujos.ingeniero_habilitado_flujo import IngenieroHabilitadoFlujo
from .domain.services.orchestrators.auth_orchestrator import AuthOrchestrator
from .domain.services.orchestrators.ingeniero_habilitado_orchestrator import IngenieroHabilitadoOrchestrator
from .infrastructure.services import ICipClient, CipClientSimulator, RealCipClient


class UsuariosModule(Module):
    """
    Módulo DI para el paquete usuarios.

    Vincula:
    - AuthCoreService (operaciones síncronas)
    - PerfilIngenieroCoreService (operaciones síncronas de perfil ingeniero)
    - AuthFlujo (flujos asíncronos, depende de AuthCoreService)
    - IngenieroHabilitadoFlujo (flujos asíncronos, depende de ICipClient y PerfilIngenieroCoreService)
    - AuthOrchestrator (fachada ligera, depende de AuthFlujo)
    - IngenieroHabilitadoOrchestrator (fachada ligera, depende de IngenieroHabilitadoFlujo)
    - ICipClient (implementación del cliente CIP)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Servicios de auth — ámbito singleton
        binder.bind(AuthCoreService, to=AuthCoreService, scope=singleton)
        binder.bind(AuthFlujo, to=AuthFlujo, scope=singleton)
        binder.bind(AuthOrchestrator, to=AuthOrchestrator, scope=singleton)

        # Servicios de ingeniero habilitado
        # En DEBUG: usar simulador para desarrollo sin API real
        # En producción: usar cliente real cuando esté disponible
        # Check env var first (set by conftest.py in tests), then fall back to settings.
        # This allows conftest.py to force simulator usage even when running with
        # development.py settings that have CIP_USE_SIMULATOR = False.
        env_simulator = os.environ.get('CIP_USE_SIMULATOR', '').lower()
        if env_simulator in ('true', '1', 'yes'):
            use_simulator = True
        elif env_simulator in ('false', '0', 'no'):
            use_simulator = False
        else:
            use_simulator = getattr(settings, 'CIP_USE_SIMULATOR', settings.DEBUG)
        if use_simulator:
            binder.bind(ICipClient, to=CipClientSimulator, scope=singleton)
        else:
            binder.bind(ICipClient, to=RealCipClient, scope=singleton)
        binder.bind(PerfilIngenieroCoreService, to=PerfilIngenieroCoreService, scope=singleton)
        binder.bind(IngenieroHabilitadoFlujo, to=IngenieroHabilitadoFlujo, scope=singleton)
        binder.bind(IngenieroHabilitadoOrchestrator, to=IngenieroHabilitadoOrchestrator, scope=singleton)
