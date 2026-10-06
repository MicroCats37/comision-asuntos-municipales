"""
Result DTOs for RH Detalle Delegado (nested shape).
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class EspecialidadMinimalResult(BaseModel):
    """Minimal especialidad for nested output."""
    id: str
    nombre: Optional[str] = None


class MunicipalidadNestedResult(BaseModel):
    """Nested municipalidad for LiquidacionGeneral nested output."""
    id: str
    nombre: Optional[str] = None


class TipoLiquidacionNestedResult(BaseModel):
    """Nested tipo_liquidacion for LiquidacionGeneral nested output."""
    id: str
    codigo: Optional[str] = None
    nombre: Optional[str] = None


class LiquidacionGeneralNestedResult(BaseModel):
    """Nested LiquidacionGeneral inside DelegadoLiquidacionResult."""
    id: str
    expediente: Optional[str] = None
    numero_revision: Optional[int] = None
    numero: Optional[int] = None
    municipalidad: Optional[MunicipalidadNestedResult] = None
    tipo_liquidacion: Optional[TipoLiquidacionNestedResult] = None


class DelegadoMinimalResult(BaseModel):
    """Minimal Delegado info for nested output."""
    id: str
    cip: Optional[str] = None
    nombre_completo: Optional[str] = None


class DelegadoLiquidacionResult(BaseModel):
    """Nested LiquidacionDelegado result with its relations."""
    id: str
    numero_rh: Optional[str] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    delegado: Optional[DelegadoMinimalResult] = None
    liquidacion: Optional[LiquidacionGeneralNestedResult] = None
    especialidad: Optional[EspecialidadMinimalResult] = None


class DetalleDelegadoRowResult(BaseModel):
    """Result DTO for a single DetalleHonorarioDelegado row — nested shape."""

    id: str  # UUID string
    # Frozen financial fields from DetalleHonorarioDelegado
    imp_bruto: Decimal
    sub_total: Optional[Decimal] = None
    renta_cip: Optional[Decimal] = None
    aporte_codemu: Optional[Decimal] = None
    fondo_comun: Optional[Decimal] = None
    neto_honorario: Optional[Decimal] = None
    # Nested LiquidacionDelegado
    delegado_liquidacion: Optional[DelegadoLiquidacionResult] = None
