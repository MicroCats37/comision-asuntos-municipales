from pydantic import BaseModel
import uuid
from decimal import Decimal
from typing import Optional, List


class EspecialidadResult(BaseModel):
    """Domain DTO for nested especialidad in cotizacion detail."""
    id: str
    nombre: str


class CotizacionM2Result(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización M2."""
    area_m2: Decimal
    costo_por_m2: Decimal
    tarifa_id: str
    derecho_id: str
    minimo: Decimal
    maximo: Optional[Decimal] = None
    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal


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
    tarifa_id: str
    especialidad: Optional[EspecialidadResult] = None
    porcentaje_aplicado: Decimal
    subtotal: Decimal


class CotizacionPorcentajeObraResult(BaseModel):
    """DTO de dominio interno que transporta el cálculo y metadata de cotización PorcentajeObra."""
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: str
    detalles: List[CotizacionPorcentajeObraDetalleResult]
    total_subtotal: Decimal
    total: Decimal
