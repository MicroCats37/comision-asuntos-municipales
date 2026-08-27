"""
Presentation schemas — Esquemas HTTP para Finanzas.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Field
from core.types import BaseSchema


class VariablesFinancierasOut(BaseSchema):
    """Variables financieras vigentes para mostrar en formulario."""
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV (ISO)")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT (ISO)")


class ReciboHonorarioDelegadoCrearIn(BaseSchema):
    """
    Schema de entrada para crear un ReciboHonorarioDelegado.

    Contrato 2 — Patrón 3: JSON Estricto.
    """
    liquidacion_delegado_id: uuid.UUID = Field(
        ..., description="FK a LiquidacionDelegado"
    )


class ReciboHonorarioInspectorCrearIn(BaseSchema):
    """
    Schema de entrada para crear un ReciboHonorarioInspector.

    Contrato 2 — Patrón 3: JSON Estricto.
    """
    liquidacion_inspector_id: uuid.UUID = Field(
        ..., description="FK a LiquidacionInspector"
    )
    inspecciones_mes: int = Field(
        ...,
        ge=1,
        description="Inspecciones liquidadas en el mes",
    )


# ── Nested minimal schemas for list endpoint ────────────────────────────────────

class TipoLiquidacionMinimalOut(BaseSchema):
    """TipoLiquidacion minimal — codigo y nombre."""
    codigo: str
    nombre: str


class LiquidacionGeneralMinimalOut(BaseSchema):
    """LiquidacionGeneral summary for list item."""
    id: uuid.UUID
    expediente: str
    numero_revision: int
    sub_total: Decimal
    total: Decimal
    fecha_registro: datetime
    tipo_liquidacion: TipoLiquidacionMinimalOut
    municipalidad_nombre: str
    proyecto_denominacion: str


class DelegadoMinimalOut(BaseSchema):
    """Delegado + PerfilIngeniero minimal for list item."""
    id: uuid.UUID
    cip: str
    dni: str
    nombre_completo: str


class EspecialidadMinimalOut(BaseSchema):
    """EspecialidadRevision minimal for list item."""
    id: uuid.UUID
    nombre: str


class ReciboHonorarioCalculoOut(BaseSchema):
    """Agrupa cálculos matemáticos del recibo."""
    sub_total: Decimal
    imp_bruto: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal
    honorario: Decimal


class LiquidacionEspecificaMinimalOut(BaseSchema):
    """LiquidacionEspecifica minimal para recibos."""
    id: uuid.UUID
    numero: int


class ReciboHonorarioDelegadoOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioDelegado en lista paginada.

    Incluye montos del recibo + resúmenes anidados de liquidacion_general,
    delegado y especialidad.
    """
    id: uuid.UUID
    liquidacion_delegado_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralMinimalOut
    liquidacion_especifica: LiquidacionEspecificaMinimalOut
    delegado: DelegadoMinimalOut
    especialidad: EspecialidadMinimalOut
    calculo: ReciboHonorarioCalculoOut
    created_at: datetime


class InspectorMinimalOut(BaseSchema):
    """Inspector + PerfilIngeniero minimal for list item."""
    id: uuid.UUID
    cip: str
    dni: str
    nombre_completo: str


class ReciboHonorarioInspectorCalculoOut(BaseSchema):
    """Agrupa cálculos matemáticos del recibo del inspector."""
    inspecciones_programadas: int
    costo_por_inspeccion: Decimal
    inspecciones_mes: int
    monto_bruto: Decimal
    inspecciones_pagadas: int
    saldo_inspecciones: int
    sub_total: Decimal
    tasa_descuento_aplicada: Decimal
    descuento: Decimal
    honorarios: Decimal


class ReciboHonorarioInspectorOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioInspector en lista paginada.

    Incluye montos del recibo + resúmenes anidados de liquidacion_general,
    inspector y especialidad.
    """
    id: uuid.UUID
    liquidacion_inspector_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralMinimalOut
    liquidacion_especifica: LiquidacionEspecificaMinimalOut
    inspector: InspectorMinimalOut
    especialidad: EspecialidadMinimalOut
    calculo: ReciboHonorarioInspectorCalculoOut
    created_at: datetime


# ── RH Inspector Mensual (Cotización/Creación) ─────────────────────────────────

class RHInspectorCotizarItemOut(BaseSchema):
    """Item individual en la cotización del RH mensual del inspector."""
    exp_liqui: str = Field(..., description="Expediente de la liquidación")
    liquidacion_inspector_id: uuid.UUID = Field(..., description="ID de LiquidacionInspector (asignación inspector-IO)")
    liquidacion_categoria_visitas_id: uuid.UUID = Field(..., description="ID de la IO (LiquidacionPorCategoriaVisitas)")
    nombre_propietario: str = Field(..., description="Nombre del propietario del proyecto")
    importe_bruto: float = Field(..., description="Sub total de LiquidacionGeneral (total de referencia sin IGV)")
    inspecciones_programadas: int = Field(..., description="Visitas programadas en la IO")
    inspecciones_liquidadas: int = Field(..., description="Inspecciones liquidadas en este RH")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Inspecciones pagadas acumuladas hasta el periodo anterior")
    costo_por_inspeccion: float = Field(..., description="Costo por inspección")
    monto_contribuido: float = Field(..., description="Monto contribuido de esta IO")
    saldo_disponible: int = Field(..., description="Saldo de visitas disponibles antes de esta cotización (programadas - pagadas_historicas)")
    saldo_restante: int = Field(..., description="Saldo restante después de esta cotización (programadas - pagadas_historicas - cantidad_visitas)")


class RHInspectorTotalesOut(BaseSchema):
    """Totales calculados para la cotización del RH mensual."""
    sub_total: float = Field(..., description="Sub total del mes (suma de montos)")
    descuento: float = Field(..., description="Descuento sobre el total")
    honorarios: float = Field(..., description="Honorarios a pagar")
    tasa_descuento_aplicada: float = Field(..., description="Tasa de descuento aplicada (ej 0.20)")


class RHInspectorCotizarOut(BaseSchema):
    """Schema de salida para la cotización/creación del RH mensual del inspector."""
    inspector: InspectorMinimalOut
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    items: list[RHInspectorCotizarItemOut] = Field(default_factory=list, description="Detalle por liquidación")
    totales: RHInspectorTotalesOut
    escala_descuento_id: uuid.UUID = Field(..., description="Escala de descuento aplicada")


# ── Inspector Candidatas (RH Mensual) ─────────────────────────────────────────

class InspectorCandidataItemOut(BaseSchema):
    """Item individual en el listado de candidatas del inspector para RH mensual."""
    liquidacion_inspector_id: uuid.UUID = Field(..., description="ID de LiquidacionInspector (asignación inspector-IO)")
    liquidacion_categoria_visitas_id: uuid.UUID = Field(..., description="ID de la IO (LiquidacionPorCategoriaVisitas)")
    liquidacion_general_id: uuid.UUID = Field(..., description="ID de la LiquidacionGeneral")
    expediente: str = Field(..., description="Expediente de la liquidación")
    numero_revision: int = Field(..., description="Número de revisión")
    fecha_registro: str = Field(..., description="Fecha de registro (ISO)")
    inspector_nombre: str = Field(..., description="Nombre completo del inspector")
    inspector_cip: str = Field(..., description="CIP del inspector")
    inspector_dni: str = Field(..., description="DNI del inspector")
    especialidad_nombre: str = Field(..., description="Nombre de la especialidad de revisión")
    nombre_propietario: str = Field(..., description="Nombre del propietario del proyecto")
    cantidad_visitas: int = Field(..., description="Visitas programadas en la IO")
    inspecciones_pagadas: int = Field(..., description="Inspecciones ya pagadas hasta el periodo anterior")
    saldo_disponible: int = Field(..., description="Saldo de visitas disponibles")
    costo_por_inspeccion: float = Field(..., description="Costo por inspección (sub_total / cantidad_visitas)")
    total_liquidacion: float = Field(..., description="Total de la liquidación")
    sub_total_liquidacion: float = Field(..., description="Sub total de la liquidación")


class InspectorCandidatosOut(BaseSchema):
    """Schema de salida para el listado de candidatas del inspector."""
    inspector_id: uuid.UUID = Field(..., description="ID del inspector")
    inspector_nombre: str = Field(..., description="Nombre completo del inspector")
    inspector_cip: str = Field(..., description="CIP del inspector")
    inspector_dni: str = Field(..., description="DNI del inspector")
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    candidatos: list[InspectorCandidataItemOut] = Field(default_factory=list, description="Lista de candidatas con saldo disponible")
    total: int = Field(..., description="Total de candidatas")


# ── RH Delegado Mensual (Cotización/Creación) ─────────────────────────────────

class RHDelegadoCotizarItemOut(BaseSchema):
    """Item individual en la cotización del RH mensual del delegado."""
    exp_liqui: str = Field(..., description="Expediente de la liquidación")
    liquidacion_delegado_id: Optional[uuid.UUID] = Field(None, description="ID de la LiquidacionDelegado (None para liquidaciones candidatadas)")
    imp_bruto: float = Field(..., description="Importe bruto del detalle porcentual")
    fecha_revision: Optional[str] = Field(None, description="Fecha de revisión (ISO)")
    numero_revision: Optional[int] = Field(None, description="Número de revisión")
    total_liquidacion: Optional[float] = Field(None, description="Total de la liquidación")
    sub_total_liquidacion: Optional[float] = Field(None, description="Sub total de la liquidación")
    numero_rh: Optional[str] = Field(None, description="Número de RH")
    renta_cip: Optional[float] = Field(None, description="Renta CIP (25%) — deducción por item")
    aporte_codemu: Optional[float] = Field(None, description="Aporte CODEMU (5%) — deducción por item")
    fondo_comun: Optional[float] = Field(None, description="Fondo Común (10%) — deducción por item")
    neto_honorario: Optional[float] = Field(None, description="Neto honorario — deducción por item")


class RHDelegadoTotalesOut(BaseSchema):
    """Totales calculados para la cotización del RH mensual del delegado."""
    sub_total: float = Field(..., description="Sub total del mes (suma de imp_bruto)")
    renta_cip: float = Field(..., description="Renta CIP (25%)")
    aporte_codemu: float = Field(..., description="Aporte CODEMU (5%)")
    fondo_comun: float = Field(..., description="Fondo Común (10%)")
    neto_honorario: float = Field(..., description="Neto Honorario")





class RHDelegadoCotizarOut(BaseSchema):
    """Schema de salida para la cotización/creación del RH mensual del delegado."""
    delegado: DelegadoMinimalOut
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    items: list[RHDelegadoCotizarItemOut] = Field(default_factory=list, description="Detalle por liquidación")
    totales: RHDelegadoTotalesOut


# ── RH Delegado Mensual — Listado ─────────────────────────────────────────────

class RHDelegadoMensualDetalleOut(BaseSchema):
    """Detalle individual en el listado de RH mensual."""
    expediente: str = Field(..., description="Expediente de la liquidación")
    imp_bruto: float = Field(..., description="Importe bruto del detalle")


class RHDelegadoMensualTotalesOut(BaseSchema):
    """Totales del RH mensual listado."""
    sub_total: float
    renta_cip: float
    aporte_codemu: float
    fondo_comun: float
    neto_honorario: float


class RHDelegadoMensualListItemOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioDelegadoMensual en lista paginada.

    Muestra: id, periodo, fecha_registro, delegado, totales, y lista de detalles
    (expediente + imp_bruto) agrupados en el mes.
    """
    id: uuid.UUID
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    delegado: DelegadoMinimalOut
    totales: RHDelegadoMensualTotalesOut
    detalles: list[RHDelegadoMensualDetalleOut] = Field(
        default_factory=list, description="Lista de detalles con expediente e imp_bruto"
    )


# ── RH Inspector Mensual — Listado ─────────────────────────────────────────────

class RHInspectorMensualDetalleOut(BaseSchema):
    """Detalle individual en el listado de RH mensual del inspector."""
    expediente: str = Field(..., description="Expediente de la liquidación")
    nombre_propietario: str = Field(..., description="Nombre del propietario del proyecto")
    importe_bruto: float = Field(..., description="Sub total de LiquidacionGeneral (total de referencia)")
    inspecciones_programadas: int = Field(..., description="Visitas programadas en la IO")
    inspecciones_liquidadas: int = Field(..., description="Inspecciones liquidadas en este RH")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Inspecciones pagadas acumuladas hasta el periodo anterior")
    costo_por_inspeccion: float = Field(..., description="Costo por inspección")
    monto_contribuido: float = Field(..., description="Monto contribuido (inspecciones_liquidadas * costo_por_inspeccion)")
    saldo_restante: int = Field(..., description="Saldo restante después de esta liquidación")


class RHInspectorMensualTotalesOut(BaseSchema):
    """Totales del RH mensual del inspector listado."""
    inspecciones_programadas: int = Field(..., description="Total inspecciones programadas")
    inspecciones_liquidadas: int = Field(..., description="Total inspecciones liquidadas en el mes")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Total inspecciones pagadas hasta mes anterior")
    saldo_restante: int = Field(..., description="Saldo restante total")
    sub_total: float = Field(..., description="Sub total del mes")
    descuento: float = Field(..., description="Descuento aplicado")
    honorarios: float = Field(..., description="Honorarios a pagar")
    tasa_descuento_aplicada: float = Field(..., description="Tasa de descuento aplicada")


class RHInspectorMensualListItemOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioInspectorMensual en lista paginada.

    Muestra: id, periodo, fecha_registro, inspector, totales, y lista de detalles
    agrupados en el mes.
    """
    id: uuid.UUID
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    inspector: InspectorMinimalOut
    totales: RHInspectorMensualTotalesOut
    detalles: list[RHInspectorMensualDetalleOut] = Field(
        default_factory=list, description="Lista de detalles por IO"
    )

