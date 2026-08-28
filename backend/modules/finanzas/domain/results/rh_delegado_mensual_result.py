"""
RH Delegado Mensual results — DTOs internos para cotización del RH mensual del delegado.

Results heredan de pydantic.BaseModel (no BaseSchema).
"""
from pydantic import BaseModel


class RHDelegadoCotizarItemResult(BaseModel):
    """
    Item individual en la cotización del RH mensual del delegado.
    """
    exp_liqui: str
    liquidacion_general_id: str  # UUID string
    especialidad_revision_id: str  # UUID string
    liquidacion_delegado_id: str | None = None  # filled by crear, None in cotizar
    imp_bruto: float
    fecha_revision: str | None = None  # ISO date string
    numero_revision: int | None = None
    total_liquidacion: float | None = None
    sub_total_liquidacion: float | None = None
    renta_cip: float | None = None  # 25% CIP — per item
    aporte_codemu: float | None = None  # 5% — per item
    fondo_comun: float | None = None  # 10% — per item
    neto_honorario: float | None = None  # per item
    numero_rh: str | None = None
    periodo: int | None = None
    mes: int | None = None
    dictamen_revision: str | None = None
    fecha_presentacion: str | None = None  # ISO date string


class RHDelegadoTotalesResult(BaseModel):
    """
    Totales calculados para la cotización del RH mensual del delegado.
    """
    sub_total: float
    renta_cip: float
    aporte_codemu: float
    fondo_comun: float
    neto_honorario: float


class DelegadoRHMinimalResult(BaseModel):
    """
    Información mínima del delegado anidada en el RH.
    """
    id: str
    nombre_completo: str
    cip: str
    dni: str


class RHDelegadoCotizarResult(BaseModel):
    """
    Resultado completo de la cotización del RH mensual del delegado.
    """
    delegado: DelegadoRHMinimalResult
    periodo: str
    items: list[RHDelegadoCotizarItemResult]
    totales: RHDelegadoTotalesResult


# ── List Result DTOs ───────────────────────────────────────────────────────────


class RHDelegadoMensualDetalleResult(BaseModel):
    """
    Detalle individual de un RH mensual (una LiquidacionDelegado agrupada).
    """
    expediente: str
    imp_bruto: float
    periodo: int | None = None
    mes: int | None = None


class RHDelegadoMensualTotalesResult(BaseModel):
    """Totales del RH mensual listado."""
    sub_total: float
    renta_cip: float
    aporte_codemu: float
    fondo_comun: float
    neto_honorario: float


class RHDelegadoMensualListItemResult(BaseModel):
    """
    Item en la lista paginada de RecibosHonorariosDelegadoMensuales.
    """
    id: str
    periodo: str
    fecha_registro: str  # ISO datetime string
    delegado: DelegadoRHMinimalResult
    totales: RHDelegadoMensualTotalesResult
    detalles: list[RHDelegadoMensualDetalleResult]


class RHDelegadoMensualListResult(BaseModel):
    """
    Resultado de la lista paginada de RH mensuales del delegado.
    """
    items: list[RHDelegadoMensualListItemResult]
    total: int
