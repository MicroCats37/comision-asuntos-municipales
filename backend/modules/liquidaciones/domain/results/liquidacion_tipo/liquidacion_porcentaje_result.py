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
    tarifa_aplicada_id: Optional[str] = None
    especialidad: Optional[EspecialidadResult] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal


class LiquidacionPorcentajeObraResult(BaseModel):
    """Result del motor PorcentajeObra persistido."""
    id: str
    liquidacion_general_id: str
    tipo_tramite: Optional[str] = None
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[str] = None
    detalles: List[DetallePorcentajeObraResult]
