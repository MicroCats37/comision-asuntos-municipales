"""
Módulo Liquidaciones — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from .domain.services.core.liquidacion_edificaciones_core_service import LiquidacionesEdificacionesService
from .domain.services.core.proyectista_core_service import ProyectistaService
from .domain.services.core.proyecto_core_service import ProyectoService
from .domain.services.core.liquidaciones_nuevas_core import (
    HabilitacionUrbanaCoreService,
    MecanicaSuelosCoreService,
    ImpactoVialCoreService,
    TaludesCoreService,
    InspeccionObraCoreService,
)
from .domain.services.flujos.liquidacion_edificaciones_flujo import LiquidacionesEdificacionesFlujo
from .domain.services.flujos.proyectista_flujo import ProyectistaFlujo
from .domain.services.flujos.proyecto_flujo import ProyectoFlujo
from .domain.services.flujos.habilitacion_urbana_flujo import HabilitacionUrbanaFlujo
from .domain.services.flujos.mecanica_suelos_flujo import MecanicaSuelosFlujo
from .domain.services.flujos.impacto_vial_flujo import ImpactoVialFlujo
from .domain.services.flujos.taludes_flujo import TaludesFlujo
from .domain.services.flujos.inspeccion_obra_flujo import InspeccionObraFlujo
from .domain.services.orchestrators.liquidacion_edificaciones_orchestrator import LiquidacionesEdificacionesOrchestrator
from .domain.services.orchestrators.proyectista_orchestrator import ProyectistaOrchestrator
from .domain.services.orchestrators.proyecto_orchestrator import ProyectoOrchestrator
from .domain.services.orchestrators.habilitacion_urbana_orchestrator import HabilitacionUrbanaOrchestrator
from .domain.services.orchestrators.mecanica_suelos_orchestrator import MecanicaSuelosOrchestrator
from .domain.services.orchestrators.impacto_vial_orchestrator import ImpactoVialOrchestrator
from .domain.services.orchestrators.taludes_orchestrator import TaludesOrchestrator
from .domain.services.orchestrators.inspeccion_obra_orchestrator import InspeccionObraOrchestrator
from .domain.services.orchestrators.delegados_batch_orchestrator import DelegadosBatchOrchestrator


class LiquidacionesModule(Module):
    """
    Módulo DI para el paquete liquidaciones.

    Vincula:
    - LiquidacionesEdificacionesService (operaciones síncronas)
    - ProyectistaService (operaciones síncronas de proyectista)
    - ProyectoService (operaciones síncronas de proyecto)
    - HabilitacionUrbanaCoreService, MecanicaSuelosCoreService,
      ImpactoVialCoreService, TaludesCoreService, InspeccionObraCoreService
    - LiquidacionesEdificacionesFlujo, ProyectistaFlujo, ProyectoFlujo
    - HabilitacionUrbanaFlujo, MecanicaSuelosFlujo, ImpactoVialFlujo,
      TaludesFlujo, InspeccionObraFlujo
    - LiquidacionesEdificacionesOrchestrator, ProyectistaOrchestrator, ProyectoOrchestrator
    - HabilitacionUrbanaOrchestrator, MecanicaSuelosOrchestrator,
      ImpactoVialOrchestrator, TaludesOrchestrator, InspeccionObraOrchestrator
    - DelegadosBatchOrchestrator (Fase 3 — batch de liquidacion delegados)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Core services
        binder.bind(LiquidacionesEdificacionesService, to=LiquidacionesEdificacionesService, scope=singleton)
        binder.bind(ProyectistaService, to=ProyectistaService, scope=singleton)
        binder.bind(ProyectoService, to=ProyectoService, scope=singleton)
        binder.bind(HabilitacionUrbanaCoreService, to=HabilitacionUrbanaCoreService, scope=singleton)
        binder.bind(MecanicaSuelosCoreService, to=MecanicaSuelosCoreService, scope=singleton)
        binder.bind(ImpactoVialCoreService, to=ImpactoVialCoreService, scope=singleton)
        binder.bind(TaludesCoreService, to=TaludesCoreService, scope=singleton)
        binder.bind(InspeccionObraCoreService, to=InspeccionObraCoreService, scope=singleton)
        # Flujos
        binder.bind(LiquidacionesEdificacionesFlujo, to=LiquidacionesEdificacionesFlujo, scope=singleton)
        binder.bind(ProyectistaFlujo, to=ProyectistaFlujo, scope=singleton)
        binder.bind(ProyectoFlujo, to=ProyectoFlujo, scope=singleton)
        binder.bind(HabilitacionUrbanaFlujo, to=HabilitacionUrbanaFlujo, scope=singleton)
        binder.bind(MecanicaSuelosFlujo, to=MecanicaSuelosFlujo, scope=singleton)
        binder.bind(ImpactoVialFlujo, to=ImpactoVialFlujo, scope=singleton)
        binder.bind(TaludesFlujo, to=TaludesFlujo, scope=singleton)
        binder.bind(InspeccionObraFlujo, to=InspeccionObraFlujo, scope=singleton)
        # Orchestrators
        binder.bind(LiquidacionesEdificacionesOrchestrator, to=LiquidacionesEdificacionesOrchestrator, scope=singleton)
        binder.bind(ProyectistaOrchestrator, to=ProyectistaOrchestrator, scope=singleton)
        binder.bind(ProyectoOrchestrator, to=ProyectoOrchestrator, scope=singleton)
        binder.bind(HabilitacionUrbanaOrchestrator, to=HabilitacionUrbanaOrchestrator, scope=singleton)
        binder.bind(MecanicaSuelosOrchestrator, to=MecanicaSuelosOrchestrator, scope=singleton)
        binder.bind(ImpactoVialOrchestrator, to=ImpactoVialOrchestrator, scope=singleton)
        binder.bind(TaludesOrchestrator, to=TaludesOrchestrator, scope=singleton)
        binder.bind(InspeccionObraOrchestrator, to=InspeccionObraOrchestrator, scope=singleton)
        # Orchestrators batch
        binder.bind(DelegadosBatchOrchestrator, to=DelegadosBatchOrchestrator, scope=singleton)
