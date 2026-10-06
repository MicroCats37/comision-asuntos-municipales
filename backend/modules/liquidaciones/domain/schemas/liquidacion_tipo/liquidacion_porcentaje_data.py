"""
DTOs de dominio para el motor de cálculo PorcentajeObra (Edificaciones).

Sigue el patrón de liquidacion_m2_data.py pero con las particularidades
del cálculo porcentual (un Detalle por tarifa aplicada).
"""
from decimal import Decimal
from typing import List, Optional
from pydantic import Field
from core.types import BaseSchema
from modules.liquidaciones.domain.constants import TipoLiquidacion


class DatosPorcentajeObra(BaseSchema):
    """Datos básicos de entrada para cálculo porcentual."""
    valor_declarado: Optional[Decimal] = Field(None, description="Valor total del proyecto")


class TarifaPorcentajeObraAplicada(BaseSchema):
    """
    Tarifa aplicada (resuelta por FK).

    With tarifa-unica-especialidades: especialidad_id/especialidad_nombre are passed
    explicitly from the input/DTO (from LiquidacionEspecialidadDisponibles), NOT
    read from TarifaPorcentajeObra.especialidad (that FK no longer exists).
    """
    tarifa_id: str
    porcentaje_liquidacion: Decimal
    especialidad_id: str
    especialidad_nombre: Optional[str] = None


class LiquidacionPorcentajeObraData(BaseSchema):
    """Datos completos para crear un cálculo porcentual."""
    datos: DatosPorcentajeObra
    tarifas: List[TarifaPorcentajeObraAplicada] = Field(
        default_factory=list,
        description="Tarifas a aplicar (vacío = auto-fill con todas las vigentes)",
    )
    tipo_tramite: Optional[str] = None  # FUTURE: activar cuando el frontend lo envíe
    override_subtotal: Optional[Decimal] = Field(
        default=None,
        description="Legacy bypass: when set, usar este subtotal directamente en lugar de calcularlo (bypasses Steps 1-5)",
    )
    override_total: Optional[Decimal] = Field(
        default=None,
        description="Legacy bypass: when set AND override_subtotal is set, usar este total directamente (bypasses IGV recalculation). Both must be set together.",
    )


class DetallePorcentajeObraData(BaseSchema):
    """
    Cálculo de un detalle individual (uno por tarifa/especialidad).

    Shadow Mode: `subtotal` se conserva exactamente como estaba (downstream readers
    no deben romperse). Los nuevos campos de alta precisión permiten cálculos exactos
    sin drift de céntimos:
    - `importe_parcial`: valor teórico por especialidad, redondeado a 2 decimales.
    - `ajuste_redondeo`: 0.00 para todos los detalles excepto el último, que recibe
      la diferencia para que SUM(subtotal) == subtotal_total exactamente.
    """
    tarifa_aplicada: Optional[TarifaPorcentajeObraAplicada] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal  # Shadow Mode: preserved exactly as-is for backward compatibility
    especialidad_id: Optional[str] = None
    importe_parcial: Optional[Decimal] = Field(
        default=Decimal("0.00"),
        description="Importe parcial de alta precisión (theoretical_value redondeado).",
    )
    ajuste_redondeo: Optional[Decimal] = Field(
        default=Decimal("0.00"),
        description="Ajuste de redondeo (0.00 para todos, último detalle recibe el remainder).",
    )


class CotizacionPorcentajeObraData(BaseSchema):
    """Resultado completo del cálculo (antes de persistir)."""
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None  # SUM de tarifas
    tipo_tramite: Optional[str] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[str] = None
    detalles: List[DetallePorcentajeObraData]
    total_subtotal: Decimal  # SUM de detalles.subtotal (post-clamping)
    total: Decimal  # SUM de detalles.total (post-clamping)
