"""
Módulo Liquidaciones — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder

from .domain.services.core.liquidacion_edificaciones_core_service import LiquidacionesEdificacionesService
from .domain.services.core.proyectista_core_service import ProyectistaService
from .domain.services.core.proyecto_core_service import ProyectoService
from .domain.services.flujos.liquidacion_edificaciones_flujo import LiquidacionesEdificacionesFlujo
from .domain.services.flujos.proyectista_flujo import ProyectistaFlujo
from .domain.services.flujos.proyecto_flujo import ProyectoFlujo
from .domain.services.orchestrators.liquidacion_edificaciones_orchestrator import LiquidacionesEdificacionesOrchestrator
from .domain.services.orchestrators.proyectista_orchestrator import ProyectistaOrchestrator
from .domain.services.orchestrators.proyecto_orchestrator import ProyectoOrchestrator


class LiquidacionesModule(Module):
    """
    Módulo DI para el paquete liquidaciones.

    Vincula:
    - LiquidacionesEdificacionesService (operaciones síncronas)
    - ProyectistaService (operaciones síncronas de proyectista)
    - LiquidacionesEdificacionesFlujo (flujos asíncronos, depende de Service)
    - ProyectistaFlujo (flujos asíncronos de proyectista)
    - LiquidacionesEdificacionesOrchestrator (fachada ligera, depende de Flujo)
    - ProyectistaOrchestrator (fachada ligera de proyectista)

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Core services
        binder.bind(LiquidacionesEdificacionesService, to=LiquidacionesEdificacionesService, scope=singleton)
        binder.bind(ProyectistaService, to=ProyectistaService, scope=singleton)
        binder.bind(ProyectoService, to=ProyectoService, scope=singleton)
        # Flujos
        binder.bind(LiquidacionesEdificacionesFlujo, to=LiquidacionesEdificacionesFlujo, scope=singleton)
        binder.bind(ProyectistaFlujo, to=ProyectistaFlujo, scope=singleton)
        binder.bind(ProyectoFlujo, to=ProyectoFlujo, scope=singleton)
        # Orchestrators
        binder.bind(LiquidacionesEdificacionesOrchestrator, to=LiquidacionesEdificacionesOrchestrator, scope=singleton)
        binder.bind(ProyectistaOrchestrator, to=ProyectistaOrchestrator, scope=singleton)
        binder.bind(ProyectoOrchestrator, to=ProyectoOrchestrator, scope=singleton)
