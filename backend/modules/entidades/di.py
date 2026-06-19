"""
Módulo Entidades — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from django.conf import settings
from injector import Module, singleton, Binder

from .domain.services.entidades_core_service import EntidadesCoreService
from .domain.services.flujos.entidad_flujo import EntidadFlujo
from .domain.services.flujos.consulta_externo_flujo import (
    ConsultaSunatFlujo,
    ConsultaReniecFlujo,
)
from .domain.services.orchestrators.entidad_orchestrator import EntidadesOrchestrator
from .domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator
from .domain.ports import ISunatClient, IReniecClient
from .infrastructure.services import (
    SunatClientSimulator,
    ReniecClientSimulator,
    RealSunatClient,
    RealReniecClient,
)


class EntidadesModule(Module):
    """
    Módulo DI para el paquete entidades.

    Vincula:
    - EntidadesCoreService (operaciones síncronas)
    - EntidadFlujo (flujos asíncronos, depende de CoreService)
    - EntidadesOrchestrator (fachada ligera, depende de Flujo)
    - ISunatClient → SunatClientSimulator o RealSunatClient (según DEBUG)
    - IReniecClient → ReniecClientSimulator o RealReniecClient (según DEBUG)
    - ConsultaSunatFlujo, ConsultaReniecFlujo
    - ConsultaOrchestrator

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # ── Core Services ──────────────────────────────────────────────────────
        binder.bind(EntidadesCoreService, to=EntidadesCoreService, scope=singleton)

        # ── Flujos ─────────────────────────────────────────────────────────────
        binder.bind(EntidadFlujo, to=EntidadFlujo, scope=singleton)
        binder.bind(ConsultaSunatFlujo, to=ConsultaSunatFlujo, scope=singleton)
        binder.bind(ConsultaReniecFlujo, to=ConsultaReniecFlujo, scope=singleton)

        # ── Orchestrators ──────────────────────────────────────────────────────
        binder.bind(EntidadesOrchestrator, to=EntidadesOrchestrator, scope=singleton)
        binder.bind(ConsultaOrchestrator, to=ConsultaOrchestrator, scope=singleton)

        # ── External Clients ──────────────────────────────────────────────────
        # En DEBUG: usar simuladores para desarrollo
        # En producción: usar clientes reales (cuando estén implementados)
        #
        # # TODO: Cuando se implementen los clientes reales, cambiar a:
        # if settings.DEBUG:
        #     binder.bind(ISunatClient, to=SunatClientSimulator, scope=singleton)
        #     binder.bind(IReniecClient, to=ReniecClientSimulator, scope=singleton)
        # else:
        #     binder.bind(ISunatClient, to=RealSunatClient, scope=singleton)
        #     binder.bind(IReniecClient, to=RealReniecClient, scope=singleton)

        binder.bind(ISunatClient, to=SunatClientSimulator, scope=singleton)
        binder.bind(IReniecClient, to=ReniecClientSimulator, scope=singleton)