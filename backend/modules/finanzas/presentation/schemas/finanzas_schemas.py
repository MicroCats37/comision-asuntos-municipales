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


class ReciboHonorarioCrearIn(BaseSchema):
    """
    Schema de entrada para crear un ReciboHonorarioDelegado.

    Contrato 2 — Patrón 3: JSON Estricto.
    """
    liquidacion_delegado_id: uuid.UUID = Field(
        ..., description="FK a LiquidacionDelegado"
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
    codigo: str
    nombre: str


class ReciboHonorarioDelegadoOut(BaseSchema):
    """
    Schema de salida para un ReciboHonorarioDelegado en lista paginada.

    Incluye montos del recibo + resúmenes anidados de liquidacion_general,
    delegado y especialidad.
    """
    id: uuid.UUID
    liquidacion_delegado_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralMinimalOut
    delegado: DelegadoMinimalOut
    especialidad: EspecialidadMinimalOut
    sub_total: Decimal
    imp_bruto: Decimal
    renta_cip: Decimal
    aporte_codemu: Decimal
    fondo_comun: Decimal
    neto_honorario: Decimal
    honorario: Decimal
    created_at: datetime
