"""
Presentation schemas — Esquemas HTTP para Finanzas.
"""
from ninja import Schema, Field


class VariablesFinancierasOut(Schema):
    """Variables financieras vigentes para mostrar en formulario."""
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV (ISO)")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT (ISO)")
