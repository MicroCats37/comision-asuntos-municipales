"""
Presentation schemas — Esquemas HTTP compartidos para liquidación.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
Contiene únicamente schemas compartidos de cotización (dispatcher) y tarifas vigentes.
Los schemas de entrada y salida por especialidad están en sus archivos por liquidación.
"""

import uuid
from ninja import Field
from typing import Optional
from pydantic import model_validator
from core.types import BaseSchema


# =============================================================================
# Cotización schemas de entrada (dispatcher — compartidos por M2 e Inspeccion)
# =============================================================================


class CotizarLiquidacionM2In(BaseSchema):
    """
    Payload para cotizar liquidaciones M2 (HU, MS, IV, TAL) sin guardar en BD.

    La cotización calcula el derecho usando la tarifa resolveda por tipo_liquidacion.
    """

    tipo_liquidacion: str = Field(
        ...,
        description="Tipo de liquidación: HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL o TALUDES.",
    )
    area_solicitada: float = Field(
        ...,
        gt=0,
        description="Área solicitada en metros cuadrados.",
    )
    # Tarifas IDs: array de exactamente 1 elemento si se proporciona
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a usar en la cotización. Debe ser exactamente 1 si se proporciona.",
    )


class CotizarLiquidacionM2WrapperIn(BaseSchema):
    """Wrapper para cotizar M2 — acepta { liquidacion: {...} }."""

    liquidacion: CotizarLiquidacionM2In


class CotizarLiquidacionInspeccionObraIn(BaseSchema):
    """
    Payload para cotizar Inspección de Obra sin guardar en BD.

    La cotización calcula el derecho usando la tarifa resolveda por categoria y tramite_accion.
    """

    cantidad_visitas: int = Field(
        ...,
        ge=1,
        description="Cantidad de visitas de inspección (mínimo 1).",
    )
    categoria: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Categoría de inspección: A, B, C, etc.",
    )
    # Tarifas IDs: array de exactamente 1 elemento si se proporciona
    tarifas_ids: list[uuid.UUID] = Field(
        default=None,
        min_length=1,
        description="IDs de tarifas a usar en la cotización. Debe ser exactamente 1 si se proporciona.",
    )


class CotizarLiquidacionInspeccionObraWrapperIn(BaseSchema):
    """Wrapper para cotizar Inspección de Obra — acepta { liquidacion: {...} }."""

    liquidacion: CotizarLiquidacionInspeccionObraIn


# =============================================================================
# Schemas de salida — helper para cotización M2
# =============================================================================


class TarifaM2Out(BaseSchema):
    """Tarifa M2 en respuesta."""

    id: uuid.UUID
    costo_por_m2: float
    area_m2: float
    derecho_minimo: float
    derecho_maximo: Optional[float]


class LiquidacionM2CalculoOut(BaseSchema):
    """Datos del cálculo por M2 en respuesta."""

    area_solicitada: float
    area_base_calculo: float
    derecho: float
    tarifa: TarifaM2Out


class TotalesOut(BaseSchema):
    """Totales de la liquidación."""

    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


# =============================================================================
# Cotización schemas de salida — M2
# =============================================================================


class CotizacionM2RevisionOut(BaseSchema):
    """Revisión M2 en respuesta de cotización."""

    area_solicitada: float
    area_base_calculo: float
    derecho: float
    tarifa: TarifaM2Out


class CotizacionM2MetadataOut(BaseSchema):
    """Metadata adicional en respuesta de cotización M2."""

    igv_valor: float
    uit_valor: float
    area_solicitada: Optional[float] = None


class CotizacionM2QuoteOut(BaseSchema):
    """Respuesta completa de cotización por M2 sin persistencia."""

    numero_revision: int
    calculo_m2: CotizacionM2RevisionOut
    totales: TotalesOut
    metadata: CotizacionM2MetadataOut

    @model_validator(mode="wrap")
    def serialize_model(self, handler):
        """Rename metadata to _metadata in JSON output per API contract."""
        data = handler(self)
        if hasattr(data, "model_dump"):
            # Convert nested models recursively to plain dicts (Pydantic v2)
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        # Safely rename metadata to _metadata
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


# =============================================================================
# Schemas de salida — helper para cotización Visitas
# =============================================================================


class TarifaVisitasOut(BaseSchema):
    """Tarifa de visitas en respuesta."""

    id: uuid.UUID
    costo_por_visita: float
    visitas_minimas: int


class LiquidacionVisitasCalculoOut(BaseSchema):
    """Datos del cálculo por visitas en respuesta."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: float
    categoria: str
    tarifa: TarifaVisitasOut


# =============================================================================
# Cotización schemas de salida — Visitas
# =============================================================================


class CotizacionVisitasRevisionOut(BaseSchema):
    """Revisión de visitas en respuesta de cotización."""

    cantidad_visitas: int
    visitas_base_calculo: int
    derecho: float
    categoria: str
    tarifa: TarifaVisitasOut


class CotizacionVisitasMetadataOut(BaseSchema):
    """Metadata adicional en respuesta de cotización de visitas."""

    igv_valor: float
    uit_valor: float
    cantidad_visitas: Optional[int] = None


class CotizacionVisitasQuoteOut(BaseSchema):
    """Respuesta completa de cotización por visitas sin persistencia."""

    numero_revision: int
    calculo_visitas: CotizacionVisitasRevisionOut
    totales: TotalesOut
    metadata: CotizacionVisitasMetadataOut

    @model_validator(mode="wrap")
    def serialize_model(self, handler):
        """Rename metadata to _metadata in JSON output per API contract."""
        data = handler(self)
        if hasattr(data, "model_dump"):
            # Convert nested models recursively to plain dicts (Pydantic v2)
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        # Safely rename metadata to _metadata
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


# =============================================================================
# Variables financieras schemas
# =============================================================================


class VariablesFinancierasOut(BaseSchema):
    """Variables financieras para mostrar en formulario."""

    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT")


# =============================================================================
# Tarifas vigentes schemas
# =============================================================================


class TarifaVigenteM2Out(BaseSchema):
    """Tarifa M2 vigente para selector en formulario."""

    tarifa_id: uuid.UUID = Field(..., description="ID de TarifaLiquidacionBase (úsalo en tarifas_ids del payload)")
    detalle_id: uuid.UUID = Field(..., description="ID de TarifaPorMetroCuadrado")
    costo_por_m2: float = Field(..., description="Costo por metro cuadrado (S/)")
    area_m2: float = Field(..., description="Área m² base para aplicar este costo")
    derecho_minimo: float = Field(..., description="Derecho mínimo a cobrar (S/)")
    derecho_maximo: Optional[float] = Field(None, description="Derecho máximo a cobrar (S/), null = sin límite")
    habilitada: bool = Field(..., description="Si la tarifa está habilitada para uso")


class TarifasVigentesM2Out(BaseSchema):
    """Respuesta de tarifas M2 vigentes para formulario."""

    tarifas: list[TarifaVigenteM2Out]


class TarifaVigenteVisitaOut(BaseSchema):
    """Tarifa de inspección de obra vigente para selector en formulario."""

    tarifa_id: uuid.UUID = Field(..., description="ID de TarifaLiquidacionBase (úsalo en tarifas_ids del payload)")
    detalle_id: uuid.UUID = Field(..., description="ID de TarifaPorCategoriaVisitas")
    costo_por_visita: float = Field(..., description="Costo por visita (S/)")
    visitas_minimas: int = Field(..., description="Cantidad mínima de visitas para aplicar este costo")
    categoria: str = Field(..., description="Categoría de inspección: CATEGORIA_A, CATEGORIA_B, CATEGORIA_C")
    habilitada: bool = Field(..., description="Si la tarifa está habilitada para uso")


class TarifasVigentesVisitasOut(BaseSchema):
    """Respuesta de tarifas de inspección de obra vigentes para formulario."""

    tarifas: list[TarifaVigenteVisitaOut]


# =============================================================================
# TarifaPorcentajeObra schemas (Edificaciones-style — usado por IV y Taludes)
# =============================================================================


class TarifaVigentePorcentajeOut(BaseSchema):
    """
    Tarifa porcentual vigente para selector en formulario de IV y Taludes.

    Representa una tarifa basada en TarifaPorcentajeObra (no M2).
    """

    tarifa_id: uuid.UUID = Field(..., description="ID de TarifaLiquidacionBase (úsalo en tarifas_ids del payload)")
    detalle_id: uuid.UUID = Field(..., description="ID de TarifaPorcentajeObra")
    porcentaje_liquidacion: float = Field(..., description="Porcentaje de liquidación (fracción decimal, ej. 0.0015 para 0.15%)")
    porcentaje_minimo_uit: float = Field(..., description="Porcentaje mínimo UIT (fracción decimal)")
    derecho_minimo: float = Field(..., description="Derecho mínimo absoluto a cobrar (S/)")
    derecho_maximo: Optional[float] = Field(None, description="Derecho máximo absoluto a cobrar (S/), null = sin límite")
    habilitada: bool = Field(..., description="Si la tarifa está habilitada para uso")


class TarifasVigentesPorcentajeOut(BaseSchema):
    """Respuesta de tarifas porcentuales vigentes para formulario (IV y Taludes)."""

    tarifas: list[TarifaVigentePorcentajeOut]
