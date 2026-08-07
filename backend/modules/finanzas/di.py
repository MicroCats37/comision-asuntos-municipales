"""
Módulo Finanzas — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
"""
from injector import Module, singleton, Binder


class FinanzasModule(Module):
    """
    Módulo DI para el paquete finanzas.

    Vincula:
    - (暂时禁用) FinanzasCoreService — 等待重建
    - (暂时禁用) FinanzasOrchestrator — 等待重建

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # TODO: 重建 IGV/UIT 服务后重新启用
        # binder.bind(FinanzasCoreService, to=FinanzasCoreService, scope=singleton)
        # binder.bind(FinanzasOrchestrator, to=FinanzasOrchestrator, scope=singleton)
        pass
