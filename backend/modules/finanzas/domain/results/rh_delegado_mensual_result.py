"""
RH Delegado Mensual results — DTOs internos para cotización del RH mensual del delegado.

Results heredan de pydantic.BaseModel (no BaseSchema).
"""
import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class LiquidacionComprobanteMinimalResult(BaseModel):
    """
    Datos mínimos del comprobante activo asociado a una LiquidacionGeneral.
    """
    tipo_comprobante: str | None = None
    serie: str | None = None
    numero: str | None = None
    fecha_emision: str | None = None  # ISO date string


class RHDelegadoCotizarItemResult(BaseModel):
    """
    Item individual en la cotización del RH mensual del delegado.
    """
    exp_liqui: str
    liquidacion_general_id: str  # UUID string
    especialidad_revision_id: str  # UUID string
    liquidacion_delegado_id: str | None = None  # filled by crear, None in cotizar
    delegado_operacion_id: str | None = None  # DelegadoOperacion ID — filled from top-level input
    imp_bruto: Decimal
    fecha_revision: str | None = None  # ISO date string
    numero_revision: int | None = None
    total_liquidacion: Decimal | None = None
    sub_total_liquidacion: Decimal | None = None
    renta_cip: Decimal | None = None  # Renta CIP (25%) — por ítem
    aporte_codemu: Decimal | None = None  # 5% — per item
    fondo_comun: Decimal | None = None  # 10% — per item
    neto_honorario: Decimal | None = None  # per item
    numero_rh: str | None = None
    periodo: int | None = None
    mes: int | None = None
    dictamen_revision: str | None = None
    fecha_presentacion: str | None = None  # ISO date string
    # Specific liquidation numero (e.g. Edificaciones numero) — resolved from the
    # one-to-one specific model (LiquidacionEdificacion, LiquidacionTaludes, etc.)
    liquidacion_especifica_numero: int | None = None
    # Active comprobante for this liquidation (activo=True)
    comprobante_activo: LiquidacionComprobanteMinimalResult | None = None


class RHDelegadoTotalesResult(BaseModel):
    """
    Totales calculados para la cotización del RH mensual del delegado.
    """
    sub_total: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal


class DelegadoRHMinimalResult(BaseModel):
    """
    Información mínima del delegado anidada en el RH.
    """
    id: str
    nombre_completo: str
    cip: str
    dni: Optional[str] = None


class RHDelegadoVariablesCalculoResult(BaseModel):
    """
    Variables de cálculo usadas en la cotización del RH mensual del delegado.
    Tasas vigentes extraídas de TasaDelegado.
    """
    tasa_renta_cip: Decimal  # e.g. Decimal("0.25")
    tasa_aporte_codemu: Decimal  # e.g. Decimal("0.05")
    tasa_fondo_comun: Decimal  # e.g. Decimal("0.10")
    tasa_delegado_id: uuid.UUID | None = None  # Frozen FK to TasaDelegado; None when listing legacy records without tasa


class RHDelegadoCotizarResult(BaseModel):
    """
    Resultado completo de la cotización del RH mensual del delegado.
    """
    delegado: DelegadoRHMinimalResult
    periodo: int | None = None
    mes: int | None = None
    items: list[RHDelegadoCotizarItemResult]
    totales: RHDelegadoTotalesResult
    variables_calculo: RHDelegadoVariablesCalculoResult


# ── List Result DTOs ───────────────────────────────────────────────────────────


class RHDelegadoMensualDetalleResult(BaseModel):
    """
    Detalle individual de un RH mensual (una LiquidacionDelegado agrupada).

    Incluye los mismos campos por fila que RHDelegadoCotizarItemResult para que
    el frontend pueda reconstruir la tabla/card sin pérdida de datos tras
    listar o ver el detalle de un ReciboHonorarioDelegadoMensual.
    """
    liquidacion_delegado_id: str
    expediente: str
    fecha_revision: str | None = None
    numero_revision: int | None = None
    total_liquidacion: Decimal | None = None
    sub_total_liquidacion: Decimal | None = None
    numero_rh: str | None = None
    imp_bruto: Decimal
    renta_cip: Decimal | None = None
    aporte_codemu: Decimal | None = None
    fondo_comun: Decimal | None = None
    neto_honorario: Decimal | None = None
    periodo: int | None = None
    mes: int | None = None
    dictamen_revision: str | None = None
    fecha_presentacion: str | None = None
    delegado_operacion_id: str | None = None  # From LiquidacionDelegado.delegado_operacion
    # Número de la liquidación específica (e.g. Edificaciones numero) — resolved from the
    # one-to-one specific model (LiquidacionEdificacion, LiquidacionTaludes, etc.)
    liquidacion_especifica_numero: int | None = None
    # Active comprobante for this liquidation (activo=True)
    comprobante_activo: LiquidacionComprobanteMinimalResult | None = None


class RHDelegadoMensualTotalesResult(BaseModel):
    """Totales del RH mensual listado."""
    sub_total: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal


class DelegadoOperacionContextResult(BaseModel):
    """
    Contexto completo de la operatividad de un delegado,
    extraído de DelegadoOperacion para mostrar en listados de RH.
    """
    id: str  # UUID string of DelegadoOperacion
    municipalidad_id: str
    municipalidad_nombre: str
    tipo_liquidacion_id: str | None = None  # nullable
    tipo_liquidacion_codigo: str | None = None
    tipo_liquidacion_nombre: str | None = None
    especialidad_id: str
    especialidad_nombre: str
    tipo: str  # TITULAR or ALTERNO


class RHDelegadoMensualListItemResult(BaseModel):
    """
    Item en la lista paginada de RecibosHonorariosDelegadoMensuales.
    """
    id: str
    periodo: int | None = None
    mes: int | None = None
    fecha_registro: str  # ISO datetime string
    delegado: DelegadoRHMinimalResult
    totales: RHDelegadoMensualTotalesResult
    detalles: list[RHDelegadoMensualDetalleResult]
    variables_calculo: RHDelegadoVariablesCalculoResult
    delegado_operacion_id: str | None = None  # From ReciboHonorarioDelegadoMensual.delegado_operacion
    delegado_operacion_context: DelegadoOperacionContextResult | None = None  # Full context when available


class RHDelegadoMensualListResult(BaseModel):
    """
    Resultado de la lista paginada de RH mensuales del delegado.
    """
    items: list[RHDelegadoMensualListItemResult]
    total: int
