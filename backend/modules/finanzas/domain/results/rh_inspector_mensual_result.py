"""
RH Inspector Mensual results — DTOs internos para cotización del RH mensual.

Results heredan de pydantic.BaseModel (no BaseSchema).
Cumple con contrato 3C: domain/results/ = DTOs internos.
"""
from pydantic import BaseModel


class RHInspectorCotizarItemResult(BaseModel):
    """
    Item individual en la cotización del RH mensual del inspector.
    """
    exp_liqui: str
    liquidacion_inspector_id: str
    liquidacion_categoria_visitas_id: str
    nombre_propietario: str  # from LiquidacionGeneral.proyecto.nombre_propietario
    importe_bruto: float  # sub_total of LiquidacionGeneral (total de referencia sin IGV)
    inspecciones_programadas: int
    inspecciones_liquidadas: int
    inspecciones_pagadas_hasta_mes_anterior: int  # accumulated historical paid inspections
    costo_por_inspeccion: float
    monto_contribuido: float
    saldo_disponible: int  # available BEFORE this quote: programdas - pagadas_historicas
    saldo_restante: int  # remaining AFTER this quote: programadas - pagadas_historicas - cantidad_visitas


class RHInspectorTotalesResult(BaseModel):
    """
    Totales calculados para la cotización del RH mensual.
    """
    sub_total: float
    descuento: float
    honorarios: float
    tasa_descuento_aplicada: float


class InspectorRHMinimalResult(BaseModel):
    """
    Información mínima del inspector anidada en el RH.
    """
    id: str
    nombre_completo: str
    cip: str
    dni: str


class RHInspectorCotizarResult(BaseModel):
    """
    Resultado completo de la cotización del RH mensual del inspector.
    """
    inspector: InspectorRHMinimalResult
    periodo: str
    items: list[RHInspectorCotizarItemResult]
    totales: RHInspectorTotalesResult
    escala_descuento_id: str


# ── RH Inspector Mensual — Listado ───────────────────────────────────────────


class RHInspectorMensualDetalleResult(BaseModel):
    """
    Detalle individual de un RH mensual del inspector (una LiquidacionPorCategoriaVisitas).
    """
    expediente: str  # from LiquidacionGeneral.expediente
    nombre_propietario: str  # from LiquidacionGeneral.proyecto.nombre_propietario
    importe_bruto: float  # sub_total of LiquidacionGeneral
    inspecciones_programadas: int  # cantidad_visitas from LiquidacionPorCategoriaVisitas
    inspecciones_liquidadas: int  # inspecciones_liquidadas from DetalleHonorarioInspector
    inspecciones_pagadas_hasta_mes_anterior: int  # derived from RegistroPagoInspector
    costo_por_inspeccion: float
    monto_contribuido: float  # inspecciones_liquidadas * costo_por_inspeccion
    saldo_restante: int  # inspecciones_programadas - inspecciones_pagadas_hasta_mes_anterior - inspecciones_liquidadas


class RHInspectorMensualTotalesResult(BaseModel):
    """Totales del RH mensual del inspector listado."""
    inspecciones_programadas: int
    inspecciones_liquidadas: int
    inspecciones_pagadas_hasta_mes_anterior: int
    saldo_restante: int
    sub_total: float
    descuento: float
    honorarios: float
    tasa_descuento_aplicada: float


class RHInspectorMensualListItemResult(BaseModel):
    """
    Item en la lista paginada de RecibosHonorariosInspectorMensuales.
    """
    id: str
    periodo: str
    fecha_registro: str  # ISO datetime string
    inspector: InspectorRHMinimalResult
    totales: RHInspectorMensualTotalesResult
    detalles: list[RHInspectorMensualDetalleResult]
