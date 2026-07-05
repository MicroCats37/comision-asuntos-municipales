"""
Domain schemas — DTOs internos para los nuevos formularios de liquidación.

Usa BaseModel de Pydantic (puro, sin validaciones de sanitización de strings).
Estos DTOs son internos y se usan para transferir datos entre capas.
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


class VariablesFinancierasResult(BaseModel):
    """Variables financieras vigentes (IGV y UIT)."""

    igv_valor: Decimal
    igv_periodo_inicio: date
    uit_valor: Decimal
    uit_periodo_inicio: date


# =============================================================================
# Resultado base para liquidación específica
# =============================================================================


class LiquidacionNuevaBaseResult(BaseModel):
    """
    Resultado base para los 5 nuevos formularios de liquidación.

    Campos comunes a todas las liquidaciones específicas.
    """

    liquidacion_id: uuid.UUID
    liquidacion_public_id: str
    numero_revision: int
    estado: str
    fecha_creacion: str
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    proyecto_direccion: Optional[str]
    proyecto_entidad_id: Optional[uuid.UUID]
    proyecto_entidad_tipo: Optional[str]
    proyecto_entidad_nombre: Optional[str]
    proyecto_entidad_ruc: Optional[str]
    municipalidad_id: uuid.UUID
    municipalidad_nombre: str
    expediente: Optional[str] = None
    observacion: Optional[str]
    igv_valor: Decimal
    uit_valor: Decimal
    totales_subtotal: Decimal
    totales_igv: Decimal
    totales_total_liquidacion: Decimal
    totales_total_a_pagar: Decimal


class LiquidacionHabilitacionUrbanaResult(LiquidacionNuevaBaseResult):
    """Resultado completo de una liquidación de habilitación urbana."""

    pass


class LiquidacionMecanicaSuelosResult(LiquidacionNuevaBaseResult):
    """Resultado completo de una liquidación de mecánica de suelos."""

    pass


class LiquidacionImpactoVialResult(LiquidacionNuevaBaseResult):
    """Resultado completo de una liquidación de impacto vial."""

    pass


class LiquidacionTaludesResult(LiquidacionNuevaBaseResult):
    """Resultado completo de una liquidación de taludes."""

    pass


class LiquidacionInspeccionObraResult(LiquidacionNuevaBaseResult):
    """Resultado completo de una liquidación de inspección de obra."""

    pass


# =============================================================================
# Wrapper Results — incluyen cálculo data para presenters de Phase 5
# (El cálculo no vive en LiquidacionXxxResult base para mantener
# compatibilidad con el patrón existente de presenters que reciben
# el cálculo como parámetro separado)
# =============================================================================


class LiquidacionM2ResultConCalculo(BaseModel):
    """
    Wrapper que combina LiquidacionM2Result con sus datos de cálculo M2.

    Evita tener que pasar el cálculo como argumento separado al presenter.
    """

    result: "LiquidacionM2Result"
    calculo_m2: "LiquidacionM2CalculoData"


class LiquidacionInspeccionObraResultConCalculo(BaseModel):
    """
    Wrapper que combina LiquidacionInspeccionObraResult con sus datos de cálculo visitas.
    """

    result: "LiquidacionInspeccionObraResult"
    calculo_visitas: "LiquidacionVisitasCalculoData"


# Alias para uso directo en import
LiquidacionHabilitacionUrbanaResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionMecanicaSuelosResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionImpactoVialResultConCalculo = LiquidacionM2ResultConCalculo
LiquidacionTaludesResultConCalculo = LiquidacionM2ResultConCalculo


# =============================================================================
# Cálculo DTOs — datos intermedios de cálculo por M2
# =============================================================================


class TarifaM2CalculoData(BaseModel):
    """Tarifa en resultado de cálculo por metro cuadrado."""

    id: uuid.UUID
    costo_por_m2: Decimal
    area_minima: Decimal
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


# =============================================================================
# Listado DTOs — items paginados para listado de liquidaciones
# =============================================================================


class LiquidacionNuevaListItem(BaseModel):
    """Item de lista paginada de liquidaciones nuevas."""

    id: uuid.UUID
    numero_revision: int
    estado: str
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float
    tipo_liquidacion: str


class LiquidacionNuevaPaginatedResult(BaseModel):
    """Resultado paginado para listado de liquidaciones nuevas."""

    items: list[LiquidacionNuevaListItem]
    total: int
