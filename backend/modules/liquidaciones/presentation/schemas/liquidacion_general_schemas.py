"""
Presentation schemas — Esquemas HTTP para Liquidaciones General.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
"""
import uuid
from ninja import Field
from typing import Optional
from pydantic import ConfigDict
from core.types import BaseSchema


class ProyectoGeneralOut(BaseSchema):
    """Proyecto básico para respuesta general."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str] = None


class EntidadGeneralOut(BaseSchema):
    """Entidad básica para respuesta general."""
    id: Optional[uuid.UUID] = None
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    ruc: Optional[str] = None


class LiquidacionGeneralOut(BaseSchema):
    """
    Schema HTTP de respuesta para endpoints de lectura general de liquidaciones.

    Estructura plana con campos comunes a todos los tipos de liquidación.

    Campos:
        id, public_id, estado, tipo_liquidacion, numero_revision,
        fecha_registro, expediente, observacion,
        proyecto, entidad, municipalidad_nombre,
        subtotal, igv, total, total_a_pagar
    """
    model_config = ConfigDict(extra='allow')

    # ── Campos scalar ────────────────────────────────────────────────────────
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str
    numero_revision: int
    fecha_registro: str
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    municipalidad_nombre: Optional[str] = None
    # ── Campos anidados ─────────────────────────────────────────────────────
    proyecto: Optional[ProyectoGeneralOut] = None
    entidad: Optional[EntidadGeneralOut] = None
    # ── Campos financieros ──────────────────────────────────────────────────────
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


class TotalesListItemOut(BaseSchema):
    """Totales para item de lista."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class LiquidacionGeneralListItemOut(BaseSchema):
    """Item de lista en respuesta paginada general."""
    id: uuid.UUID
    public_id: str
    estado: str
    tipo_liquidacion: str  # Slug format: habilitacion-urbana, inspeccion-obra, etc.
    numero_revision: int
    proyecto_denominacion: str
    proyecto_public_id: str
    fecha_registro: str
    total: float
    # Campos adicionales para frontend no-edificación
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    municipalidad_id: Optional[str] = None
    municipalidad_nombre: Optional[str] = None
    # valor_caracteristico: área para M2, cantidad_visitas para IO
    valor_caracteristico: Optional[float] = None
    # Totales anidados
    totales: Optional[TotalesListItemOut] = None
