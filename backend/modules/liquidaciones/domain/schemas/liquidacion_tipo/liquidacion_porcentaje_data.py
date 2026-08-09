"""
DTOs de dominio para el motor de cálculo PorcentajeObra (Edificaciones).

Sigue el patrón de liquidacion_m2_data.py pero con las particularidades
del cálculo porcentual (un Detalle por tarifa aplicada).
"""
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from modules.liquidaciones.domain.constants import TipoLiquidacion


class DatosPorcentajeObra(BaseModel):
    """Datos básicos de entrada para cálculo porcentual."""
    valor_declarado: Decimal = Field(..., description="Valor total del proyecto")


class TarifaPorcentajeObraAplicada(BaseModel):
    """Tarifa aplicada (resuelta por FK)."""
    tarifa_id: str
    porcentaje_liquidacion: Decimal
    especialidad_id: str
    especialidad_nombre: str


class LiquidacionPorcentajeObraData(BaseModel):
    """Datos completos para crear un cálculo porcentual."""
    datos: DatosPorcentajeObra
    tarifas: List[TarifaPorcentajeObraAplicada] = Field(
        default_factory=list,
        description="Tarifas a aplicar (vacío = auto-fill con todas las vigentes)",
    )
    tipo_tramite: Optional[str] = None  # FUTURE: activar cuando el frontend lo envíe


class DetallePorcentajeObraData(BaseModel):
    """Cálculo de un detalle individual (uno por tarifa/especialidad)."""
    tarifa_aplicada: TarifaPorcentajeObraAplicada
    porcentaje_aplicado: Decimal
    subtotal: Decimal
    igv: Decimal
    uit: Decimal
    total: Decimal


class CotizacionPorcentajeObraData(BaseModel):
    """Resultado completo del cálculo (antes de persistir)."""
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal  # SUM de tarifas
    tipo_tramite: Optional[str] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal]
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: str
    detalles: List[DetallePorcentajeObraData]
    total_subtotal: Decimal  # SUM de detalles.subtotal (post-clamping)
    total: Decimal  # SUM de detalles.total (post-clamping)
