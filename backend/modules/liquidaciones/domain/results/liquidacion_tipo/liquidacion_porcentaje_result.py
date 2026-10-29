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


class AcumulacionPorcentajeObraResult(BaseModel):
    """
    Proyección vigente de la diferencia entre el padre PO y la suma de sus detalles.

    `porcentaje_acumulado` es NULL en TOTAL_EXPLICITO: el total es autoritativo y
    no hay invariante de porcentaje.
    """
    porcentaje_acumulado: Optional[Decimal] = None
    subtotal_acumulado: Decimal


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
    # ── Estrategia PO (Edificaciones). Los demás motores los dejan en None. ──
    estrategia_cotizacion: Optional[str] = None
    count_habilitadas: Optional[int] = None
    total_explicito: Optional[Decimal] = None
    porcentaje_tarifa: Optional[Decimal] = None
    tarifa_aplicada_id: Optional[str] = None
    acumulacion: Optional[AcumulacionPorcentajeObraResult] = None
