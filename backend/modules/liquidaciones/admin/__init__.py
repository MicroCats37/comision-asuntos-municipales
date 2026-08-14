"""Admin package for liquidaciones module — imports all admin submodules."""

from .catalogos_admin import (
    TipoLiquidacionAdmin,
    LiquidacionEspecialidadDisponiblesAdmin,
)
from .profesionales_admin import (
    DelegadoAdmin,
    InspectorAdmin,
    ProyectistaAdmin,
)
from .tarifas_admin import (
    TarifaLiquidacionBaseAdmin,
    TarifaPorMetroCuadradoAdmin,
    TarifaPorCategoriaVisitasAdmin,
    TarifaPorcentajeObraAdmin,
    DerechoPorcentajeObraAdmin,
    DerechoPorMetroCuadradoAdmin,
)
from .liquidacion_admin import LiquidacionGeneralAdmin, LiquidacionCodigoAdmin
from .proyecto_admin import ProyectoAdmin

__all__ = [
    "TipoLiquidacionAdmin",
    "LiquidacionEspecialidadDisponiblesAdmin",
    "DelegadoAdmin",
    "InspectorAdmin",
    "ProyectistaAdmin",
    "TarifaLiquidacionBaseAdmin",
    "TarifaPorMetroCuadradoAdmin",
    "TarifaPorCategoriaVisitasAdmin",
    "TarifaPorcentajeObraAdmin",
    "DerechoPorcentajeObraAdmin",
    "DerechoPorMetroCuadradoAdmin",
    "LiquidacionGeneralAdmin",
    "LiquidacionCodigoAdmin",
    "ProyectoAdmin",
]
