"""
Results del motor PorcentajeObra. Mapean modelos ORM a DTOs.
"""
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel


class EspecialidadResult(BaseModel):
    """Domain DTO for nested especialidad in liquidacion detail."""
    id: str
    nombre: str


class DetallePorcentajeObraResult(BaseModel):
    """Result de un Detalle persistido."""
    id: str
    tarifa_aplicada_id: str
    especialidad: Optional[EspecialidadResult] = None
    porcentaje_aplicado: Decimal
    subtotal: Decimal


class LiquidacionPorcentajeObraResult(BaseModel):
    """Result del motor PorcentajeObra persistido."""
    id: str
    liquidacion_general_id: str
    tipo_tramite: Optional[str] = None
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: str
    detalles: List[DetallePorcentajeObraResult]
