"""
RH Inspector Mensual results — DTOs internos para cotización del RH mensual.

Results heredan de pydantic.BaseModel (no BaseSchema).
Cumple con contrato 3C: domain/results/ = DTOs internos.
"""
from pydantic import BaseModel


class RHInspectorCotizarItemResult(BaseModel):
    """
    Item individual en la cotización del RH mensual del inspector.
    """
    exp_liqui: str
    liquidacion_categoria_visitas_id: str
    inspecciones_programadas: int
    inspecciones_liquidadas: int
    costo_por_inspeccion: float
    monto_contribuido: float
    saldo_disponible: int


class RHInspectorTotalesResult(BaseModel):
    """
    Totales calculados para la cotización del RH mensual.
    """
    sub_total: float
    descuento: float
    honorarios: float
    tasa_descuento_aplicada: float


class RHInspectorCotizarResult(BaseModel):
    """
    Resultado completo de la cotización del RH mensual del inspector.
    """
    inspector_id: str
    inspector_nombre: str
    inspector_cip: str
    periodo: str
    items: list[RHInspectorCotizarItemResult]
    totales: RHInspectorTotalesResult
    escala_descuento_id: str
