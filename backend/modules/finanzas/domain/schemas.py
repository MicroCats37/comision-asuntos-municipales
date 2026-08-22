"""
Domain schemas — DTOs internos para Finanzas.
"""
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class VariablesVigentesResult(BaseModel):
    """
    DTO de resultado para el caso de uso de obtener variables vigentes.

    Incluye los valores de IGV y UIT junto con sus períodos de inicio.
    """
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: date = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: date = Field(..., description="Fecha inicio período UIT")

    @classmethod
    def from_igv_uit(cls, igv, uit) -> "VariablesVigentesResult":
        """
        Factory para crear desde modelos IGV y UIT.

        Args:
            igv: Instancia del modelo IGV (o None)
            uit: Instancia del modelo UIT (o None)

        Returns:
            VariablesVigentesResult con valores o errores si no se encuentran
        """
        return cls(
            igv_valor=float(igv.valor) if igv else 0.0,
            igv_periodo_inicio=igv.periodo_inicio if igv else date.min,
            uit_valor=float(uit.valor) if uit else 0.0,
            uit_periodo_inicio=uit.periodo_inicio if uit else date.min,
        )

# ---------------------------------------------------------------------------
# RH Inspector Mensual — contratos de entrada (BaseSchema)
# ---------------------------------------------------------------------------
from core.types import BaseSchema as _BaseSchema


class RHInspectorCotizarItemIn(_BaseSchema):
    """Item individual para la cotización del RH mensual del inspector."""
    exp_liqui: str
    cantidad_visitas: int


class RHInspectorCotizarIn(_BaseSchema):
    """Payload de entrada para cotizar/crear el RH mensual del inspector."""
    cip: str
    periodo: str  # "YYYY-MM"
    items: list[RHInspectorCotizarItemIn]
