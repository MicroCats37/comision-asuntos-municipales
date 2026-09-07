"""
RH Inspector Mensual results — DTOs internos para cotización del RH mensual.

Results heredan de pydantic.BaseModel (no BaseSchema).
Cumple con contrato 3C: domain/results/ = DTOs internos.
"""
from decimal import Decimal

from pydantic import BaseModel

from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    LiquidacionComprobanteMinimalResult,
)


class RHInspectorCotizarItemResult(BaseModel):
    """
    Item individual en la cotización del RH mensual del inspector.
    """
    exp_liqui: str
    liquidacion_inspector_id: str
    liquidacion_categoria_visitas_id: str
    nombre_propietario: str  # from LiquidacionGeneral.proyecto.nombre_propietario
    importe_bruto: Decimal  # sub_total of LiquidacionGeneral (total de referencia sin IGV)
    inspecciones_programadas: int
    inspecciones_liquidadas: int
    inspecciones_pagadas_hasta_mes_anterior: int  # accumulated historical paid inspections
    costo_por_inspeccion: Decimal
    monto_contribuido: Decimal
    saldo_disponible: int  # available BEFORE this quote: programdas - pagadas_historicas
    saldo_restante: int  # remaining AFTER this quote: programada
    # Frozen math values — frozen at creation time for auditability
    escala_descuento_id: str  # FK to EscalaDescuentoInspector (frozen reference)
    sub_total: Decimal  # equals monto_contribuido (frozen at item level)
    descuento: Decimal  # proportional share of total descuento (frozen)
    honorarios: Decimal  # sub_total - descuento (frozen)
    periodo: int | None = None
    mes: int | None = None
    # Specific liquidation numero (e.g. LiquidacionInspeccionObra numero) — resolved from the
    # one-to-one specific model via LiquidacionGeneral
    liquidacion_especifica_numero: int | None = None
    # Active comprobante for this liquidation (activo=True)
    comprobante_activo: LiquidacionComprobanteMinimalResult | None = None


class RHInspectorTotalesResult(BaseModel):
    """
    Totales calculados para la cotización del RH mensual.
    """
    sub_total: Decimal
    descuento: Decimal
    honorarios: Decimal
    tasa_descuento_aplicada: Decimal


class InspectorRHMinimalResult(BaseModel):
    """
    Información mínima del inspector anidada en el RH.
    """
    id: str
    nombre_completo: str
    cip: str
    dni: str


class RangoDescuentoResult(BaseModel):
    """
    Rango de descuento con sus límites y porcentaje.
    """
    monto_minimo: Decimal
    monto_maximo: Decimal | None  # None = sin tope superior
    porcentaje_descuento: Decimal  # fracción decimal, e.g. 0.20


class RHInspectorVariablesCalculoResult(BaseModel):
    """
    Variables de cálculo usadas en la cotización del RH mensual del inspector.
    Escala de descuento vigente con el rango aplicado.
    """
    escala_id: str
    escala_nombre: str
    rango_aplicado: RangoDescuentoResult


class RHInspectorCotizarResult(BaseModel):
    """
    Resultado completo de la cotización del RH mensual del inspector.
    """
    inspector: InspectorRHMinimalResult
    periodo: int | None = None
    mes: int | None = None
    items: list[RHInspectorCotizarItemResult]
    totales: RHInspectorTotalesResult
    escala_descuento_id: str
    variables_calculo: RHInspectorVariablesCalculoResult
    inspector_operacion_id: str | None = None  # Populated from selected items on create


# ── RH Inspector Mensual — Listado ───────────────────────────────────────────


class RHInspectorMensualDetalleResult(BaseModel):
    """
    Detalle individual de un RH mensual del inspector (una LiquidacionPorCategoriaVisitas).
    """
    expediente: str  # from LiquidacionGeneral.expediente
    nombre_propietario: str  # from LiquidacionGeneral.proyecto.nombre_propietario
    distrito: str | None = None  # from LiquidacionGeneral.proyecto.distrito.nombre
    importe_bruto: Decimal  # from DetalleHonorarioInspector.importe_bruto (frozen)
    inspecciones_programadas: int  # from DetalleHonorarioInspector.inspecciones_programadas (frozen)
    inspecciones_liquidadas: int  # inspecciones_liquidadas from DetalleHonorarioInspector
    inspecciones_pagadas_hasta_mes_anterior: int  # from DetalleHonorarioInspector.inspecciones_pagadas_hasta_mes_anterior (frozen)
    costo_por_inspeccion: Decimal
    monto_contribuido: Decimal
    saldo_restante: int  # from DetalleHonorarioInspector.saldo_restante (frozen)
    # Frozen math values
    sub_total: Decimal  # frozen per-item subtotal
    descuento: Decimal  # frozen proportional descuento
    honorarios: Decimal  # frozen net honorarios (sub_total - descuento)
    # Specific liquidation numero (e.g. LiquidacionInspeccionObra numero) — resolved from
    # liquidacion_por_categoria_visitas.liquidacion_general via the inspeccion_obra one-to-one
    liquidacion_especifica_numero: int | None = None
    # Active comprobante for this liquidation (activo=True)
    comprobante_activo: "LiquidacionComprobanteMinimalResult | None" = None
    # Dates from LiquidacionInspector (through table linking inspector to lcv)
    fecha_revision: str | None = None
    fecha_presentacion: str | None = None
    dictamen_revision: str | None = None


class RHInspectorMensualTotalesResult(BaseModel):
    """Totales del RH mensual del inspector listado."""
    inspecciones_programadas: int
    inspecciones_liquidadas: int
    inspecciones_pagadas_hasta_mes_anterior: int
    saldo_restante: int
    sub_total: Decimal
    descuento: Decimal
    honorarios: Decimal
    tasa_descuento_aplicada: Decimal


class RHInspectorMensualListItemResult(BaseModel):
    """
    Item en la lista paginada de RecibosHonorariosInspectorMensuales.
    """
    id: str
    numero: int | None = None  # numero de RH (from ReciboHonorarioInspectorMensual)
    periodo: int | None = None
    mes: int | None = None
    fecha_registro: str  # ISO datetime string
    inspector: InspectorRHMinimalResult
    totales: RHInspectorMensualTotalesResult
    detalles: list[RHInspectorMensualDetalleResult]
    variables_calculo: RHInspectorVariablesCalculoResult
