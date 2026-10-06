"""
Result DTOs for RH Detalle Inspector (nested shape).
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class InspectorMinimalResult(BaseModel):
    """Minimal Inspector info for nested output."""
    id: str
    cip: Optional[str] = None
    nombre_completo: Optional[str] = None


class MunicipalidadNestedResult(BaseModel):
    """Nested municipalidad for LiquidacionGeneral nested output — inspector variant."""
    id: str
    nombre: Optional[str] = None


class TipoLiquidacionNestedResult(BaseModel):
    """Nested tipo_liquidacion for LiquidacionGeneral nested output — inspector variant."""
    id: str
    codigo: Optional[str] = None
    nombre: Optional[str] = None


class LiquidacionInspectorNestedResult(BaseModel):
    """Nested LiquidacionPorCategoriaVisitas.liquidacion_general for inspector output."""
    id: str
    expediente: Optional[str] = None
    numero_revision: Optional[int] = None
    nombre_propietario: Optional[str] = None
    numero: Optional[int] = None
    municipalidad: Optional[MunicipalidadNestedResult] = None
    tipo_liquidacion: Optional[TipoLiquidacionNestedResult] = None


class InspectorLiquidacionResult(BaseModel):
    """Nested LiquidacionInspector result with its relations."""
    id: str
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    inspector: Optional[InspectorMinimalResult] = None
    liquidacion: Optional[LiquidacionInspectorNestedResult] = None


class DetalleInspectorRowResult(BaseModel):
    """Result DTO for a single DetalleHonorarioInspector row — nested shape."""

    id: str  # UUID string
    # Frozen financial fields from DetalleHonorarioInspector
    inspecciones_liquidadas: int
    costo_por_inspeccion: Decimal
    monto_contribuido: Decimal
    saldo_restante: Optional[Decimal] = None
    importe_bruto: Optional[Decimal] = None
    inspecciones_programadas: Optional[int] = None
    inspecciones_pagadas_hasta_mes_anterior: Optional[int] = None
    sub_total: Optional[Decimal] = None
    descuento: Optional[Decimal] = None
    honorarios: Optional[Decimal] = None
    tasa_descuento: Optional[Decimal] = None
    # Nested LiquidacionInspector
    inspector_liquidacion: Optional[InspectorLiquidacionResult] = None
