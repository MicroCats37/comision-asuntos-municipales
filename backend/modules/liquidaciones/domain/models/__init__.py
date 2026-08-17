"""Domain models — re-exported from domain/models/."""

from .delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    # Backward-compatible aliases
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
)
from .tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadIngeniero, EspecialidadRevision
from .liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
)
from .liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    # Modelo de detalle para edificaciones (singular)
    LiquidacionEdificacion,
)
from .liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import LiquidacionHabilitacionUrbana
from .liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import LiquidacionMecanicaSuelos
from .liquidacion.liquidacion_especifico.liquidacion_impacto_vial import LiquidacionImpactoVial
from .liquidacion.liquidacion_especifico.liquidacion_taludes import LiquidacionTaludes
from .liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import LiquidacionInspeccionObra
from .liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from .liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
)
from .proyectista import Proyectista
from .proyecto import (
    Proyecto,
    ProyectoEmpresarial,
    ProyectoPersonaNatural,
)
from .delegado import LiquidacionDelegado
from .inspector import (
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
    LiquidacionInspector,
    # Backward-compatible aliases
    InspectorTipoLiquidacion,
    InspectorAsignacionPeriodo,
)

__all__ = [
    "Delegado",
    "DelegadoOperacion",
    "DelegadoOperacionPeriodo",
    # Backward-compatible aliases (for existing service/orchestrator code)
    "DelegadoMunicipalidad",
    "DelegadoMunicipalidadPeriodo",
    "TipoLiquidacion",
    "EspecialidadIngeniero",
    "EspecialidadRevision",
    "LiquidacionGeneral",
    "LiquidacionContacto",
    "LiquidacionDocumentos",
    # Modelo de detalle para edificaciones
    "LiquidacionEdificacion",
    # Modelos de especialidades M2 y visitas
    "LiquidacionHabilitacionUrbana",
    "LiquidacionMecanicaSuelos",
    "LiquidacionImpactoVial",
    "LiquidacionTaludes",
    "LiquidacionInspeccionObra",
    # Modelos de cálculo nuevos
    "LiquidacionPorMetroCuadrado",
    "LiquidacionPorCategoriaVisitas",
    # Modelos del refactor
    "LiquidacionProyectista",
    "TarifaPorcentajeObra",
    "TarifaLiquidacionBase",
    "LiquidacionPorcentajeObra",
    "LiquidacionPorcentajeObraDetalle",
    # Tarifas y reglas nuevas
    "TarifaPorMetroCuadrado",
    "TarifaPorCategoriaVisitas",
    "Proyectista",
    "Proyecto",
    "ProyectoEmpresarial",
    "ProyectoPersonaNatural",
    "LiquidacionDelegado",
    "Inspector",
    "InspectorOperacion",
    "InspectorOperacionPeriodo",
    "LiquidacionInspector",
    # Backward-compatible aliases (for existing service/orchestrator code)
    "InspectorTipoLiquidacion",
    "InspectorAsignacionPeriodo",
]
