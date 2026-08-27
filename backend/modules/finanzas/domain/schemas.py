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
    """
    Item individual para la cotización del RH mensual del inspector.

    Soporta dos flujos de entrada:
    1. Flujo manual (exp_liqui + cantidad_visitas): Para backward compatibility.
    2. Flujo por candidatas (liquidacion_categoria_visitas_id + cantidad_visitas):
       Permite pasar directamente el ID de la IO seleccionada desde candidates endpoint.

    Se requiere exactamente uno de: exp_liqui O liquidacion_categoria_visitas_id.
    """
    exp_liqui: Optional[str] = Field(None, description="Expediente de la liquidación (flujo manual)")
    liquidacion_categoria_visitas_id: Optional[str] = Field(
        None,
        description="ID de la LiquidacionPorCategoriaVisitas (flujo por candidatas)",
    )
    cantidad_visitas: int = Field(..., ge=1, description="Cantidad de inspecciones a liquidar")


class RHInspectorCotizarIn(_BaseSchema):
    """Payload de entrada para cotizar/crear el RH mensual del inspector."""
    cip: str
    periodo: str  # "YYYY-MM"
    items: list[RHInspectorCotizarItemIn]


# ---------------------------------------------------------------------------
# RH Delegado Mensual — contratos de entrada (BaseSchema)
# ---------------------------------------------------------------------------


class RHDelegadoCotizarItemIn(_BaseSchema):
    """
    Item individual para la cotización del RH mensual del delegado.

    usa liquidacion_general_id + especialidad_revision_id (de la candidata)
    para calcular imp_bruto directamente desde LiquidacionPorcentajeObraDetalle,
    sin requerir que LiquidacionDelegado exista aún.

    Los campos periodo, dictamen_revision, fecha_presentacion y fecha_revision
    se usan en crear() para persistir en LiquidacionDelegado.
    """
    liquidacion_general_id: str  # UUID string de CandidataOut.id
    especialidad_revision_id: str  # UUID string de CandidataOut.especialidad_candidata.id
    numero_rh: Optional[str] = None  # Número de Orden/RH — se usa en LiquidacionDelegado.numero_rh
    periodo: Optional[str] = None  # YYYY-MM — se usa en LiquidacionDelegado.periodo
    dictamen_revision: Optional[str] = None  # se usa en LiquidacionDelegado.dictamen_revision
    fecha_presentacion: Optional[date] = None  # se usa en LiquidacionDelegado.fecha_presentacion
    fecha_revision: Optional[date] = None  # se usa en LiquidacionDelegado.fecha_revision


class RHDelegadoCotizarIn(_BaseSchema):
    """Payload de entrada para cotizar/crear el RH mensual del delegado."""
    cip: str
    periodo: str  # "YYYY-MM"
    items: list[RHDelegadoCotizarItemIn]
