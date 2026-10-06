"""
CalculoHonorarioResult — DTO para el resultado puro del cálculo de honorarios.

Este DTO contiene SOLO los campos derivados del cálculo (sin contexto de BD).
Es lo que retorna el helper _calcular_honorarios() del modelo.

Cumple con contrato 3C: domain/results/ = DTOs internos, pydantic BaseModel puro.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class CalculoHonorarioResult(BaseModel):
    """
    Resultado puro del cálculo de honorarios.

    Campos: imp_bruto + 5 campos derivados. Sin FKs a la BD.
    """

    imp_bruto: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal
    honorario: Decimal


class TipoLiquidacionMinimal(BaseModel):
    """TipoLiquidacion minimal — codigo y nombre."""
    codigo: str
    nombre: str


class LiquidacionGeneralMinimal(BaseModel):
    """Resumen de LiquidacionGeneral para ítem de listado."""
    id: str
    expediente: str
    numero_revision: int
    sub_total: Decimal
    total: Decimal
    fecha_registro: str
    tipo_liquidacion: TipoLiquidacionMinimal
    municipalidad_nombre: str
    proyecto_denominacion: str


class DelegadoMinimal(BaseModel):
    """Delegado + PerfilIngeniero minimal para ítem de listado."""
    id: str
    nombre_completo: str
    cip: str
    dni: str


class EspecialidadMinimal(BaseModel):
    """EspecialidadRevision minimal para ítem de listado."""
    id: str
    nombre: str


class ReciboHonorarioCalculoResult(BaseModel):
    """Agrupa los montos y resultados matemáticos del recibo."""
    sub_total: Decimal
    imp_bruto: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal
    honorario: Decimal


class LiquidacionEspecificaMinimalResult(BaseModel):
    """LiquidacionEspecifica (Edificación, HabilitaciónUrbana, etc.) minimal."""
    id: str
    numero: int


class ReciboHonorarioDelegadoResult(BaseModel):
    """
    Resultado de dominio para un ReciboHonorarioDelegado en lista paginada.

    Incluye montos del recibo + resúmenes anidados de liquidacion_general,
    delegado y especialidad — sin dependencias ORM.
    """
    id: str
    liquidacion_delegado_id: str  # UUID string
    calculo: ReciboHonorarioCalculoResult
    created_at: datetime
    liquidacion_general: LiquidacionGeneralMinimal
    liquidacion_especifica: LiquidacionEspecificaMinimalResult
    delegado: DelegadoMinimal
    especialidad: EspecialidadMinimal


class InspectorMinimal(BaseModel):
    """Inspector + PerfilIngeniero minimal for list item."""
    id: str
    cip: str
    dni: str
    nombre_completo: str


class ReciboHonorarioInspectorCalculoResult(BaseModel):
    """Agrupa los montos y resultados matemáticos del recibo del inspector."""
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


class ReciboHonorarioInspectorResult(BaseModel):
    """
    Resultado de dominio para un ReciboHonorarioInspector en lista paginada.

    Incluye montos del recibo + resúmenes anidados de liquidacion_general,
    inspector y especialidad — sin dependencias ORM.
    """
    id: str
    liquidacion_inspector_id: str  # UUID string
    calculo: ReciboHonorarioInspectorCalculoResult
    created_at: datetime
    liquidacion_general: LiquidacionGeneralMinimal
    liquidacion_especifica: LiquidacionEspecificaMinimalResult
    inspector: InspectorMinimal
    especialidad: EspecialidadMinimal
