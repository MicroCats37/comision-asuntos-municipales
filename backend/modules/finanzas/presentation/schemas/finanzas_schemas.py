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
    dni: Optional[str] = None
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

class LiquidacionComprobanteMinimalOut(BaseSchema):
    """
    Datos mínimos del comprobante activo asociado a una LiquidacionGeneral.
    """
    tipo_comprobante: Optional[str] = Field(None, description="Tipo de comprobante (e.g. Factura, Boleta)")
    serie: Optional[str] = Field(None, description="Serie del comprobante")
    numero: Optional[str] = Field(None, description="Número del comprobante")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión (ISO)")


class RHInspectorCotizarItemOut(BaseSchema):
    """Item individual en la cotización del RH mensual del inspector."""
    exp_liqui: str = Field(..., description="Expediente de la liquidación")
    liquidacion_inspector_id: uuid.UUID = Field(..., description="ID de LiquidacionInspector (asignación inspector-IO)")
    liquidacion_categoria_visitas_id: uuid.UUID = Field(..., description="ID de la IO (LiquidacionPorCategoriaVisitas)")
    nombre_propietario: str = Field(..., description="Nombre del propietario del proyecto")
    importe_bruto: Decimal = Field(..., description="Sub total de LiquidacionGeneral (total de referencia sin IGV)")
    inspecciones_programadas: int = Field(..., description="Visitas programadas en la IO")
    inspecciones_liquidadas: int = Field(..., description="Inspecciones liquidadas en este RH")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Inspecciones pagadas acumuladas hasta el periodo anterior")
    costo_por_inspeccion: Decimal = Field(..., description="Costo por inspección")
    monto_contribuido: Decimal = Field(..., description="Monto contribuido de esta IO")
    saldo_disponible: int = Field(..., description="Saldo de visitas disponibles antes de esta cotización (programadas - pagadas_historicas)")
    saldo_restante: int = Field(..., description="Saldo restante después de esta cotización (programadas - pagadas_historicas - cantidad_visitas)")
    periodo: Optional[int] = Field(None, description="Año de la LiquidacionInspector")
    mes: Optional[int] = Field(None, description="Mes de la LiquidacionInspector")
    # Número de la liquidación específica (ej. LiquidacionInspeccionObra número)
    liquidacion_especifica_numero: Optional[int] = Field(None, description="Número de la liquidación específica")
    # Comprobante activo asociado a la liquidación
    comprobante_activo: Optional[LiquidacionComprobanteMinimalOut] = Field(None, description="Comprobante activo de la liquidación")


class RHInspectorTotalesOut(BaseSchema):
    """Totales calculados para la cotización del RH mensual."""
    sub_total: Decimal = Field(..., description="Sub total del mes (suma de montos)")
    descuento: Decimal = Field(..., description="Descuento sobre el total")
    honorarios: Decimal = Field(..., description="Honorarios a pagar")
    tasa_descuento_aplicada: Decimal = Field(..., description="Tasa de descuento aplicada (ej 0.20)")


class RangoDescuentoOut(BaseSchema):
    """Rango de descuento con sus límites y porcentaje."""
    monto_minimo: Decimal = Field(..., description="Monto mínimo del rango")
    monto_maximo: Decimal | None = Field(None, description="Monto máximo (null = sin tope superior)")
    porcentaje_descuento: Decimal = Field(..., description="Porcentaje de descuento (fracción decimal, ej. 0.20)")


class RHInspectorVariablesCalculoOut(BaseSchema):
    """Variables de cálculo usadas en la cotización del RH mensual del inspector."""
    escala_id: str = Field(..., description="ID de la escala de descuento")
    escala_nombre: str = Field(..., description="Nombre de la escala de descuento")
    rango_aplicado: RangoDescuentoOut = Field(..., description="Rango de descuento aplicado según el monto")


class RHInspectorCotizarOut(BaseSchema):
    """Schema de salida para la cotización/creación del RH mensual del inspector."""
    inspector: InspectorMinimalOut
    periodo: Optional[int] = Field(None, description="Año del periodo (e.g. 2026)")
    mes: Optional[int] = Field(None, description="Mes del periodo (1-12)")
    items: list[RHInspectorCotizarItemOut] = Field(default_factory=list, description="Detalle por liquidación")
    totales: RHInspectorTotalesOut
    escala_descuento_id: uuid.UUID = Field(..., description="Escala de descuento aplicada")
    variables_calculo: RHInspectorVariablesCalculoOut


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
    costo_por_inspeccion: Decimal = Field(..., description="Costo por inspección (sub_total / cantidad_visitas)")
    total_liquidacion: Decimal = Field(..., description="Total de la liquidación")
    sub_total_liquidacion: Decimal = Field(..., description="Sub total de la liquidación")


class InspectorCandidatosOut(BaseSchema):
    """Schema de salida para el listado de candidatas del inspector."""
    inspector_id: uuid.UUID = Field(..., description="ID del inspector")
    inspector_nombre: str = Field(..., description="Nombre completo del inspector")
    inspector_cip: str = Field(..., description="CIP del inspector")
    inspector_dni: str = Field(..., description="DNI del inspector")
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    candidatos: list[InspectorCandidataItemOut] = Field(default_factory=list, description="Lista de candidatas con saldo disponible")
    total: int = Field(..., description="Total de candidatas")


class InspectorCandidatosPaginatedOut(BaseSchema):
    """Schema de salida paginado para el listado de candidatas del inspector."""
    inspector_id: uuid.UUID = Field(..., description="ID del inspector")
    inspector_nombre: str = Field(..., description="Nombre completo del inspector")
    inspector_cip: str = Field(..., description="CIP del inspector")
    inspector_dni: str = Field(..., description="DNI del inspector")
    periodo: str = Field(..., description="Periodo (YYYY-MM)")
    items: list[InspectorCandidataItemOut] = Field(default_factory=list, description="Lista paginada de candidatas con saldo disponible")
    total: int = Field(..., description="Total de candidatas")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Elementos por página")
    total_pages: int = Field(..., description="Total de páginas")


# ── RH Delegado Mensual (Cotización/Creación) ─────────────────────────────────

class RHDelegadoVariablesCalculoOut(BaseSchema):
    """Variables de cálculo usadas en la cotización del RH mensual del delegado."""
    tasa_renta_cip: Decimal = Field(..., description="Tasa Renta CIP (ej. 0.25)")
    tasa_aporte_codemu: Decimal = Field(..., description="Tasa Aporte CODEMU (ej. 0.05)")
    tasa_fondo_comun: Decimal = Field(..., description="Tasa Fondo Común (ej. 0.10)")


class RHDelegadoCotizarItemOut(BaseSchema):
    """Item individual en la cotización del RH mensual del delegado."""
    exp_liqui: str = Field(..., description="Expediente de la liquidación")
    liquidacion_delegado_id: Optional[uuid.UUID] = Field(None, description="ID de la LiquidacionDelegado (None para liquidaciones candidatadas)")
    delegado_operacion_id: Optional[uuid.UUID] = Field(None, description="ID de la DelegadoOperacion")
    imp_bruto: Decimal = Field(..., description="Importe bruto del detalle porcentual")
    fecha_revision: Optional[str] = Field(None, description="Fecha de revisión (ISO)")
    numero_revision: Optional[int] = Field(None, description="Número de revisión")
    total_liquidacion: Optional[Decimal] = Field(None, description="Total de la liquidación")
    sub_total_liquidacion: Optional[Decimal] = Field(None, description="Sub total de la liquidación")
    numero_rh: Optional[str] = Field(None, description="Número de RH")
    renta_cip: Optional[Decimal] = Field(None, description="Renta CIP (25%) — deducción por item")
    aporte_codemu: Optional[Decimal] = Field(None, description="Aporte CODEMU (5%) — deducción por item")
    fondo_comun: Optional[Decimal] = Field(None, description="Fondo Común (10%) — deducción por item")
    neto_honorario: Optional[Decimal] = Field(None, description="Neto honorario — deducción por item")
    # Número de la liquidación específica (e.g. Edificaciones numero)
    liquidacion_especifica_numero: Optional[int] = Field(None, description="Número de la liquidación específica")
    # Comprobante activo asociado a la liquidación
    comprobante_activo: Optional[LiquidacionComprobanteMinimalOut] = Field(None, description="Comprobante activo de la liquidación")


class RHDelegadoTotalesOut(BaseSchema):
    """Totales calculados para la cotización del RH mensual del delegado."""
    sub_total: Decimal = Field(..., description="Sub total del mes (suma de imp_bruto)")
    renta_cip: Decimal = Field(..., description="Renta CIP (25%)")
    aporte_codemu: Decimal = Field(..., description="Aporte CODEMU (5%)")
    fondo_comun: Decimal = Field(..., description="Fondo Común (10%)")
    neto_honorario: Decimal = Field(..., description="Neto Honorario")





class RHDelegadoCotizarOut(BaseSchema):
    """Schema de salida para la cotización/creación del RH mensual del delegado."""
    delegado: DelegadoMinimalOut
    periodo: Optional[int] = Field(None, description="Año del periodo (e.g. 2026)")
    mes: Optional[int] = Field(None, description="Mes del periodo (1-12)")
    items: list[RHDelegadoCotizarItemOut] = Field(default_factory=list, description="Detalle por liquidación")
    totales: RHDelegadoTotalesOut
    variables_calculo: RHDelegadoVariablesCalculoOut


# ── RH Delegado Mensual — Listado ─────────────────────────────────────────────

class RHDelegadoMensualDetalleOut(BaseSchema):
    """
    Detalle individual en el listado de RH mensual.

    Incluye todos los campos por fila (liquidacion_delegado_id, expediente,
    imp_bruto, partials, fechas, numeros) para que el frontend pueda reconstruir
    la misma tabla que muestra cotizar sin pérdida de datos.
    """
    liquidacion_delegado_id: uuid.UUID
    expediente: str = Field(..., description="Expediente de la liquidación")
    fecha_revision: str | None = Field(None, description="Fecha de revisión (ISO)")
    numero_revision: int | None = Field(None, description="Número de revisión")
    total_liquidacion: Decimal | None = Field(None, description="Total de la liquidación")
    sub_total_liquidacion: Decimal | None = Field(None, description="Subtotal de la liquidación")
    numero_rh: str | None = Field(None, description="Número de RH")
    imp_bruto: Decimal = Field(..., description="Importe bruto del detalle")
    renta_cip: Decimal | None = Field(None, description="Renta CIP (25%)")
    aporte_codemu: Decimal | None = Field(None, description="Aporte CODEMU (5%)")
    fondo_comun: Decimal | None = Field(None, description="Fondo Común (10%)")
    neto_honorario: Decimal | None = Field(None, description="Neto honorario")
    periodo: int | None = Field(None, description="Periodo (año)")
    mes: int | None = Field(None, description="Mes (1-12)")
    dictamen_revision: str | None = Field(None, description="Dictamen de revisión")
    fecha_presentacion: str | None = Field(None, description="Fecha de presentación (ISO)")
    delegado_operacion_id: Optional[uuid.UUID] = Field(None, description="ID de la DelegadoOperacion")
    # Número de la liquidación específica (e.g. Edificaciones numero)
    liquidacion_especifica_numero: Optional[int] = Field(
        None, description="Número de la liquidación específica"
    )
    # Comprobante activo asociado a la liquidación
    comprobante_activo: Optional["LiquidacionComprobanteMinimalOut"] = Field(
        None, description="Comprobante activo de la liquidación"
    )


class RHDelegadoMensualTotalesOut(BaseSchema):
    """Totales del RH mensual listado."""
    sub_total: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal


class DelegadoOperacionContextOut(BaseSchema):
    """
    Contexto completo de la operatividad del delegado en un RH mensual.

    Expone municipalidad, tipo de liquidación, especialidad y rol para mostrar
    al usuario en lugar del UUID crudo.
    """
    id: uuid.UUID = Field(..., description="ID de la DelegadoOperacion")
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    municipalidad_nombre: str = Field(..., description="Nombre de la municipalidad")
    tipo_liquidacion_id: Optional[uuid.UUID] = Field(
        None, description="ID del tipo de liquidación (nullable)"
    )
    tipo_liquidacion_codigo: Optional[str] = Field(
        None, description="Código del tipo de liquidación"
    )
    tipo_liquidacion_nombre: Optional[str] = Field(
        None, description="Nombre del tipo de liquidación"
    )
    especialidad_id: uuid.UUID = Field(..., description="ID de la especialidad de revisión")
    especialidad_nombre: str = Field(..., description="Nombre de la especialidad")
    tipo: str = Field(..., description="Rol: TITULAR o ALTERNO")


class RHDelegadoMensualListItemOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioDelegadoMensual en lista paginada.

    Muestra: id, periodo, mes, fecha_registro, delegado, totales, detalles
    (expediente + imp_bruto) agrupados en el mes, y tasas vigentes.
    """
    id: uuid.UUID
    periodo: Optional[int] = Field(None, description="Año del periodo (e.g. 2026)")
    mes: Optional[int] = Field(None, description="Mes del periodo (1-12)")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    delegado: DelegadoMinimalOut
    totales: RHDelegadoMensualTotalesOut
    detalles: list[RHDelegadoMensualDetalleOut] = Field(
        default_factory=list, description="Lista de detalles con expediente e imp_bruto"
    )
    variables_calculo: RHDelegadoVariablesCalculoOut = Field(
        description="Tasas vigentes usadas en el cálculo del RH"
    )
    delegado_operacion_id: Optional[uuid.UUID] = Field(
        None, description="ID de la DelegadoOperacion (operatividad) asociada al RH"
    )
    delegado_operacion_context: Optional[DelegadoOperacionContextOut] = Field(
        None, description="Contexto completo de la operatividad (municipalidad, tipo, especialidad, rol)"
    )


# ── RH Inspector Mensual — Listado ─────────────────────────────────────────────

class RHInspectorMensualDetalleOut(BaseSchema):
    """Detalle individual en el listado de RH mensual del inspector."""
    expediente: str = Field(..., description="Expediente de la liquidación")
    nombre_propietario: str = Field(..., description="Nombre del propietario del proyecto")
    distrito: Optional[str] = Field(
        None, description="Distrito del proyecto de la liquidación"
    )
    importe_bruto: Decimal = Field(..., description="Sub total de LiquidacionGeneral (total de referencia)")
    inspecciones_programadas: int = Field(..., description="Visitas programadas en la IO")
    inspecciones_liquidadas: int = Field(..., description="Inspecciones liquidadas en este RH")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Inspecciones pagadas acumuladas hasta el periodo anterior")
    costo_por_inspeccion: Decimal = Field(..., description="Costo por inspección")
    monto_contribuido: Decimal = Field(..., description="Monto contribuido (inspecciones_liquidadas * costo_por_inspeccion)")
    saldo_restante: int = Field(..., description="Saldo restante después de esta liquidación")
    # Número de la liquidación específica (e.g. LiquidacionInspeccionObra numero)
    liquidacion_especifica_numero: Optional[int] = Field(
        None, description="Número de la liquidación específica de IO"
    )
    # Comprobante activo asociado a la liquidación
    comprobante_activo: Optional["LiquidacionComprobanteMinimalOut"] = Field(
        None, description="Comprobante activo de la liquidación"
    )
    # Frozen math fields — populated from DetalleHonorarioInspector
    sub_total: Optional[Decimal] = Field(
        None, description="Sub total de la liquidación del mes"
    )
    descuento: Optional[Decimal] = Field(
        None, description="Descuento aplicado"
    )
    honorarios: Optional[Decimal] = Field(
        None, description="Honorarios a pagar"
    )


class RHInspectorMensualTotalesOut(BaseSchema):
    """Totales del RH mensual del inspector listado."""
    inspecciones_programadas: int = Field(..., description="Total inspecciones programadas")
    inspecciones_liquidadas: int = Field(..., description="Total inspecciones liquidadas en el mes")
    inspecciones_pagadas_hasta_mes_anterior: int = Field(..., description="Total inspecciones pagadas hasta mes anterior")
    saldo_restante: int = Field(..., description="Saldo restante total")
    sub_total: Decimal = Field(..., description="Sub total del mes")
    descuento: Decimal = Field(..., description="Descuento aplicado")
    honorarios: Decimal = Field(..., description="Honorarios a pagar")
    tasa_descuento_aplicada: Decimal = Field(..., description="Tasa de descuento aplicada")


class RHInspectorMensualListItemOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioInspectorMensual en lista paginada.

    Muestra: id, periodo, mes, fecha_registro, inspector, totales, detalles,
    y variables_calculo con la escala de descuento aplicada.
    """
    id: uuid.UUID
    periodo: Optional[int] = Field(None, description="Año del periodo (e.g. 2026)")
    mes: Optional[int] = Field(None, description="Mes del periodo (1-12)")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    inspector: InspectorMinimalOut
    totales: RHInspectorMensualTotalesOut
    detalles: list[RHInspectorMensualDetalleOut] = Field(
        default_factory=list, description="Lista de detalles por IO"
    )
    variables_calculo: RHInspectorVariablesCalculoOut = Field(
        description="Variables de cálculo con escala de descuento aplicada"
    )


# ── RH Detalle List (nested shape) ─────────────────────────────────────────────

# ── Nested schemas ──────────────────────────────────────────────────────────────

class MunicipalidadNestedOut(BaseSchema):
    """Nested municipalidad inside LiquidacionGeneralNestedOut."""
    id: uuid.UUID = Field(..., description="ID de la municipalidad")
    nombre: Optional[str] = Field(None, description="Nombre de la municipalidad")


class TipoLiquidacionNestedOut(BaseSchema):
    """Nested tipo_liquidacion inside LiquidacionGeneralNestedOut."""
    id: uuid.UUID = Field(..., description="ID del tipo de liquidación")
    codigo: Optional[str] = Field(None, description="Código del tipo")
    nombre: Optional[str] = Field(None, description="Nombre del tipo")


class LiquidacionGeneralNestedOut(BaseSchema):
    """Nested LiquidacionGeneral inside DelegadoLiquidacionOut."""
    id: uuid.UUID = Field(..., description="ID de LiquidacionGeneral")
    expediente: Optional[str] = Field(None, description="Expediente")
    numero_revision: Optional[int] = Field(None, description="Número de revisión")
    numero: Optional[int] = Field(None, description="Número de la liquidación específica")
    municipalidad: Optional[MunicipalidadNestedOut] = Field(None, description="Municipalidad")
    tipo_liquidacion: Optional[TipoLiquidacionNestedOut] = Field(None, description="Tipo de liquidación")


class EspecialidadMinimalOut(BaseSchema):
    """Minimal especialidad for nested output."""
    id: uuid.UUID = Field(..., description="ID de la especialidad")
    nombre: Optional[str] = Field(None, description="Nombre de la especialidad")


class DelegadoMinimalOut(BaseSchema):
    """Minimal Delegado info for nested output."""
    id: uuid.UUID = Field(..., description="ID del delegado")
    cip: Optional[str] = Field(None, description="CIP del delegado")
    nombre_completo: Optional[str] = Field(None, description="Nombre completo")


class DelegadoLiquidacionOut(BaseSchema):
    """
    Nested LiquidacionDelegado with its relations.

    Contains all fields that belong to LiquidacionDelegado and its FK relations
    that were previously flat in DetalleDelegadoRowOut.
    """
    id: uuid.UUID = Field(..., description="ID de LiquidacionDelegado")
    numero_rh: Optional[str] = Field(None, description="Número de RH")
    periodo: Optional[int] = Field(None, description="Año del periodo")
    mes: Optional[int] = Field(None, description="Mes (1-12)")
    dictamen_revision: Optional[str] = Field(None, description="Dictamen de revisión")
    fecha_revision: Optional[str] = Field(None, description="Fecha de revisión (ISO)")
    fecha_presentacion: Optional[str] = Field(None, description="Fecha de presentación (ISO)")
    delegado: DelegadoMinimalOut = Field(..., description="Datos del delegado")
    liquidacion: LiquidacionGeneralNestedOut = Field(..., description="Liquidación general")
    especialidad: Optional[EspecialidadMinimalOut] = Field(None, description="Especialidad de revisión")


class DetalleDelegadoRowOut(BaseSchema):
    """
    Schema de salida para una fila en el listado detalle de RH Delegado.

    Representa UN detalle individual de DetalleHonorarioDelegado — sin agrupamiento
    por recibo mensual. Filtros: delegado_id, periodo, mes.

    El endpoint es GET /finanzas/recibos-delegados/detalle.

    Shape: parent keeps financial fields only; LiquidacionDelegado fields are
    nested inside `delegado_liquidacion` per api-wrapper-presenter-contract.
    """
    id: uuid.UUID = Field(..., description="ID del DetalleHonorarioDelegado")
    # Frozen financial fields from DetalleHonorarioDelegado
    imp_bruto: Decimal = Field(..., description="Importe bruto del detalle")
    sub_total: Optional[Decimal] = Field(None, description="Sub total")
    renta_cip: Optional[Decimal] = Field(None, description="Renta CIP")
    aporte_codemu: Optional[Decimal] = Field(None, description="Aporte CODEMU")
    fondo_comun: Optional[Decimal] = Field(None, description="Fondo Común")
    neto_honorario: Optional[Decimal] = Field(None, description="Neto Honorario")
    # Nested LiquidacionDelegado
    delegado_liquidacion: DelegadoLiquidacionOut = Field(
        ..., description="Liquidación del delegado con relaciones anidadas"
    )


# ── Inspector detail row schemas ────────────────────────────────────────────────

class InspectorLiquidacionNestedOut(BaseSchema):
    """Nested LiquidacionPorCategoriaVisitas.liquidacion_general for inspector output."""
    id: uuid.UUID = Field(..., description="ID de LiquidacionGeneral")
    expediente: Optional[str] = Field(None, description="Expediente")
    numero_revision: Optional[int] = Field(None, description="Número de revisión")
    nombre_propietario: Optional[str] = Field(None, description="Nombre del propietario")
    numero: Optional[int] = Field(None, description="Número de la liquidación específica")
    municipalidad: Optional[MunicipalidadNestedOut] = Field(None, description="Municipalidad")
    tipo_liquidacion: Optional[TipoLiquidacionNestedOut] = Field(None, description="Tipo de liquidación")


class InspectorMinimalOut(BaseSchema):
    """Minimal Inspector info for nested output."""
    id: uuid.UUID = Field(..., description="ID del inspector")
    cip: Optional[str] = Field(None, description="CIP del inspector")
    nombre_completo: Optional[str] = Field(None, description="Nombre completo")


class InspectorLiquidacionOut(BaseSchema):
    """
    Nested LiquidacionInspector with its relations.

    Contains all fields that belong to LiquidacionInspector and its FK relations
    that were previously flat in DetalleInspectorRowOut.
    """
    id: uuid.UUID = Field(..., description="ID de LiquidacionInspector")
    periodo: Optional[int] = Field(None, description="Año del periodo")
    mes: Optional[int] = Field(None, description="Mes (1-12)")
    dictamen_revision: Optional[str] = Field(None, description="Dictamen de revisión")
    fecha_revision: Optional[str] = Field(None, description="Fecha de revisión (ISO)")
    fecha_presentacion: Optional[str] = Field(None, description="Fecha de presentación (ISO)")
    inspector: InspectorMinimalOut = Field(..., description="Datos del inspector")
    liquidacion: InspectorLiquidacionNestedOut = Field(..., description="Liquidación de categoría visitas")


class DetalleInspectorRowOut(BaseSchema):
    """
    Schema de salida para una fila en el listado detalle de RH Inspector.

    Representa UN detalle individual de DetalleHonorarioInspector — sin agrupamiento
    por recibo mensual. Filtros: inspector_id, periodo, mes.

    El endpoint es GET /finanzas/recibos-inspectores/detalle.

    Shape: parent keeps financial fields only; LiquidacionInspector fields are
    nested inside `inspector_liquidacion` per api-wrapper-presenter-contract.
    """
    id: uuid.UUID = Field(..., description="ID del DetalleHonorarioInspector")
    # Frozen financial fields from DetalleHonorarioInspector
    inspecciones_liquidadas: int = Field(..., description="Inspecciones liquidadas en el mes")
    costo_por_inspeccion: Decimal = Field(..., description="Costo por inspección")
    monto_contribuido: Decimal = Field(..., description="Monto contribuido")
    saldo_restante: Optional[Decimal] = Field(None, description="Saldo restante")
    importe_bruto: Optional[Decimal] = Field(None, description="Importe bruto")
    inspecciones_programadas: Optional[int] = Field(None, description="Inspecciones programadas")
    inspecciones_pagadas_hasta_mes_anterior: Optional[int] = Field(None, description="Inspecciones pagadas hasta mes anterior")
    sub_total: Optional[Decimal] = Field(None, description="Sub total")
    descuento: Optional[Decimal] = Field(None, description="Descuento")
    honorarios: Optional[Decimal] = Field(None, description="Honorarios")
    tasa_descuento: Optional[Decimal] = Field(None, description="Tasa de descuento aplicada")
    # Nested LiquidacionInspector
    inspector_liquidacion: InspectorLiquidacionOut = Field(
        ..., description="Liquidación del inspector con relaciones anidadas"
    )
