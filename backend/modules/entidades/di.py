"""
Módulo Entidades — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from django.conf import settings
from injector import Module, singleton, Binder

from .domain.services.entidades_core_service import EntidadesCoreService
from .domain.services.flujos.entidad_flujo import EntidadFlujo
from .domain.services.flujos.consulta_externo_flujo import ConsultaExternaFlujo
from .domain.services.orchestrators.entidad_orchestrator import EntidadesOrchestrator
from .domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator
from .domain.ports import IConsultaExternaClient
from .infrastructure.services import (
    ConsultaExternaSimulator,
    RealConsultaExternaClient,
)


class EntidadesModule(Module):
    """
    Módulo DI para el paquete entidades.

    Vincula:
    - EntidadesCoreService (operaciones síncronas)
    - EntidadFlujo (flujos asíncronos, depende de CoreService)
    - EntidadesOrchestrator (fachada ligera, depende de Flujo)
    - IConsultaExternaClient → ConsultaExternaSimulator o RealConsultaExternaClient (unificado)
    - ConsultaExternaFlujo
    - ConsultaOrchestrator

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # ── Core Services ──────────────────────────────────────────────────────
        binder.bind(EntidadesCoreService, to=EntidadesCoreService, scope=singleton)

        # ── Flujos ─────────────────────────────────────────────────────────────
        binder.bind(EntidadFlujo, to=EntidadFlujo, scope=singleton)
        binder.bind(ConsultaExternaFlujo, to=ConsultaExternaFlujo, scope=singleton)

        # ── Orchestrators ──────────────────────────────────────────────────────
        binder.bind(EntidadesOrchestrator, to=EntidadesOrchestrator, scope=singleton)
        binder.bind(ConsultaOrchestrator, to=ConsultaOrchestrator, scope=singleton)

        # ── External Clients (unificado) ────────────────────────────────────────
        # En DEBUG: usar simulador para desarrollo
        # En producción: usar cliente real (cuando esté implementado)
        #
        # # TODO: Cuando se implemente RealConsultaExternaClient, cambiar a:
        # if settings.DEBUG:
        #     binder.bind(IConsultaExternaClient, to=ConsultaExternaSimulator, scope=singleton)
        # else:
        #     binder.bind(IConsultaExternaClient, to=RealConsultaExternaClient, scope=singleton)

        binder.bind(IConsultaExternaClient, to=ConsultaExternaSimulator, scope=singleton)
