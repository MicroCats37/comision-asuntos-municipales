"""Domain models — re-exported from domain/models/."""

from .delegado import Delegado, MunicipalidadDelegado, PeriodoDelegado
from .especialidades import Especialidad
from .liquidacion import (
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
    TarifaPorcentajeObra,
    TarifaLiquidacionBase,
    LiquidacionPorcentajeObra,
    EspecialidadesLiquidacion,
    ReglaTarifaEdificacion,
)
from .liquidacion.liquidacion_edificaciones import (
    # Modelo de detalle para edificaciones (singular)
    LiquidacionEdificacion,
    LiquidacionEdificacionProxy,
)
from .liquidacion.liquidacion_habilitacion_urbana import LiquidacionHabilitacionUrbana
from .liquidacion.liquidacion_mecanica_suelos import LiquidacionMecanicaSuelos
from .liquidacion.liquidacion_impacto_vial import LiquidacionImpactoVial
from .liquidacion.liquidacion_taludes import LiquidacionTaludes
from .liquidacion.liquidacion_inspeccion_obra import LiquidacionInspeccionObra
from .liquidacion.calculos_tarifas import (
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from .liquidacion.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    ReglaTarifaLiquidacion,
    ReglaTarifaInspeccionObra,
)
from .proyectista import Proyectista
from .proyecto import (
    Proyecto,
    ProyectoEmpresarial,
    ProyectoPersonaNatural,
    ContactoProyecto,
)
from .liquidacion_delegado import LiquidacionDelegado

__all__ = [
    "Delegado",
    "MunicipalidadDelegado",
    "PeriodoDelegado",
    "Especialidad",
    "LiquidacionGeneral",
    "LiquidacionContacto",
    "LiquidacionDocumentos",
    # Modelo de detalle para edificaciones
    "LiquidacionEdificacion",
    "LiquidacionEdificacionProxy",
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
    "EspecialidadesLiquidacion",
    # Tarifas y reglas nuevas
    "TarifaPorMetroCuadrado",
    "TarifaPorCategoriaVisitas",
    "ReglaTarifaLiquidacion",
    "ReglaTarifaInspeccionObra",
    "Proyectista",
    "Proyecto",
    "ProyectoEmpresarial",
    "ProyectoPersonaNatural",
    "ContactoProyecto",
    "LiquidacionDelegado",
]
