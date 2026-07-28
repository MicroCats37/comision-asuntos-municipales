"""
Schemas compartidos — DTOs puros no ligados a un tipo de liquidación.

Estos DTOs son internos y se usan para transferir datos entre capas.
No contienen lógica de negocio, solo datos.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


# =============================================================================
# Contacto Inline DTO — reutilizado de schemas.py existente
# =============================================================================


class ContactoInlineData(BaseModel):
    """DTO para crear contactos inline asociados a una liquidacion."""

    nombres: str
    apellidos: str
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    principal: bool = False
    descripcion: Optional[str] = None


# =============================================================================
# Entidad inline DTO — reutilizado de schemas_proyecto.py existente
# =============================================================================


class EntidadInlineData(BaseModel):
    """DTO para crear/entidad inline upsert por numero_documento."""

    tipo_documento: str
    numero_documento: str
    razon_social: str


# =============================================================================
# Proyecto inline DTO — reutilizado de schemas_proyecto.py existente
# =============================================================================


class ProyectoInlineData(BaseModel):
    """DTO para crear proyecto inline durante primera revisión."""

    denominacion: str
    direccion: Optional[str] = None
    distrito_id: Optional[uuid.UUID] = None
    nombre_propietario: str
    entidad: EntidadInlineData


# =============================================================================
# Variables financieras DTO — resultado de variables vigentes
# =============================================================================


class IgvInfo(BaseModel):
    """Información del IGV vigente para respuestas HTTP."""
    id: uuid.UUID
    valor: float  # Fracción decimal (ej. 0.18)
    porcentaje: float  # Porcentaje (ej. 18.0)
    periodo_inicio: date


class UitInfo(BaseModel):
    """Información de la UIT vigente para respuestas HTTP."""
    id: uuid.UUID
    valor: float  # Valor en soles (ej. 5350)
    anio: int  # Año de vigencia
    periodo_inicio: date


class VariablesFinancierasInfo(BaseModel):
    """Variables financieras vigentes (IGV y UIT) para list/detail de liquidaciones."""
    igv: Optional[IgvInfo]
    uit: Optional[UitInfo]


class VariablesFinancierasResult(BaseModel):
    """Variables financieras vigentes (IGV y UIT) — formato interno del dominio."""

    igv_valor: Decimal
    igv_periodo_inicio: date
    uit_valor: Decimal
    uit_periodo_inicio: date


# =============================================================================
# Cálculo DTOs — datos intermedios de cálculo por M2
# =============================================================================


class TarifaM2CalculoData(BaseModel):
    """Tarifa en resultado de cálculo por metro cuadrado."""

    id: uuid.UUID
    costo_por_m2: Decimal
    area_m2: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal]


class LiquidacionM2CalculoData(BaseModel):
    """Datos del cálculo por metro cuadrado en resultado."""

    area_solicitada: Decimal
    area_base_calculo: Decimal
    derecho: Decimal
    tarifa: TarifaM2CalculoData


# =============================================================================
# Cálculo DTOs — datos intermedios de cálculo por categoría de visitas
# =============================================================================


class TarifaVisitasCalculoData(BaseModel):
    """Tarifa en resultado de cálculo por categoría de visitas."""

    id: uuid.UUID
    costo_por_visita: Decimal
    visitas_minimas: int


class LiquidacionVisitasCalculoData(BaseModel):
    """Datos del cálculo por categoría de visitas en resultado."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: Decimal
    categoria: str
    tarifa: TarifaVisitasCalculoData


# =============================================================================
# Cotización / Quote DTOs — resultado de cálculo sin persistencia
# =============================================================================


class CotizacionM2RevisionData(BaseModel):
    """Resultado de cálculo M2 individual en cotización."""

    area_solicitada: Decimal
    area_base_calculo: Decimal
    derecho: Decimal
    tarifa: TarifaM2CalculoData


class CotizacionVisitasRevisionData(BaseModel):
    """Resultado de cálculo de visitas individual en cotización."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: Decimal
    categoria: str
    tarifa: TarifaVisitasCalculoData


class CotizacionTotalesData(BaseModel):
    """Totales en resultado de cotización."""

    subtotal: Decimal
    igv: Decimal
    total: Decimal
    liquidacion_total: Decimal
    total_a_pagar: Decimal


class CotizacionMetadataData(BaseModel):
    """Metadata adicional en resultado de cotización."""

    igv_valor: Decimal
    uit_valor: Decimal
    area_solicitada: Optional[Decimal] = None  # Para M2
    cantidad_visitas: Optional[int] = None  # Para visitas


class CotizacionM2QuoteData(BaseModel):
    """Resultado completo de cotización por M2 — sin persistencia en BD."""

    numero_revision: int
    calculo_m2: CotizacionM2RevisionData
    totales: CotizacionTotalesData
    metadata: CotizacionMetadataData


class CotizacionVisitasQuoteData(BaseModel):
    """Resultado completo de cotización por visitas — sin persistencia en BD."""

    numero_revision: int
    calculo_visitas: CotizacionVisitasRevisionData
    totales: CotizacionTotalesData
    metadata: CotizacionMetadataData
