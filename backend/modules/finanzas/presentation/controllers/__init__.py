"""Presentation controllers — re-export all controllers."""
from .variables_controller import VariablesController
from .rh_delegado.mensual_controller import RHDelegadoMensualController
from .rh_delegado.detalle_controller import RHDelegadoDetalleController
from .rh_inspector.mensual_controller import RHInspectorMensualController
from .rh_inspector.detalle_controller import RHInspectorDetalleController

__all__ = [
    "VariablesController",
    "RHDelegadoMensualController",
    "RHDelegadoDetalleController",
    "RHInspectorMensualController",
    "RHInspectorDetalleController",
]
