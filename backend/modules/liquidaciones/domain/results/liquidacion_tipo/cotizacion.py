from pydantic import BaseModel
import uuid
from decimal import Decimal
from typing import Optional, List

from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    AcumulacionPorcentajeObraResult,
)


class EspecialidadResult(BaseModel):
    """Domain DTO for nested especialidad in cotizacion detail."""
    id: str
    nombre: str


class CotizacionM2Result(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización M2."""
    area_m2: Decimal
    costo_por_m2: Optional[Decimal] = None
    tarifa_id: Optional[str] = None
    derecho_id: Optional[str] = None
    minimo: Optional[Decimal] = None
    maximo: Optional[Decimal] = None
    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal
    igv_porcentaje: Optional[Decimal] = None
    monto_igv: Optional[Decimal] = None


class CotizacionVisitasResult(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización de Visitas."""
    cantidad_visitas: int
    categoria: str
    costo_por_visita: Decimal
    tarifa_id: str
    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal
    uit: dict
    igv: dict


class CotizacionPorcentajeObraDetalleResult(BaseModel):
    """Detalle de cotización porcentual (no persiste)."""
    tarifa_id: Optional[str] = None
    especialidad: Optional[EspecialidadResult] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal


class CotizacionPorcentajeObraResult(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización PorcentajeObra."""
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[str] = None
    detalles: List[CotizacionPorcentajeObraDetalleResult]
    total_subtotal: Decimal
    total: Decimal
    # ── Estrategia PO (Edificaciones). Los demás motores los dejan en None. ──
    estrategia_cotizacion: Optional[str] = None
    count_habilitadas: Optional[int] = None
    total_explicito: Optional[Decimal] = None
    porcentaje_tarifa: Optional[Decimal] = None
    acumulacion: Optional[AcumulacionPorcentajeObraResult] = None
