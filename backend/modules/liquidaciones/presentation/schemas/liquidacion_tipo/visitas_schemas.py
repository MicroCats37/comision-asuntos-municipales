"""
Visitas presentation schemas — Estructuras de cálculo por Visitas.

Contiene los schemas de entrada y salida reutilizables por cualquier especialidad
que use el mismo tipo de cálculo (ej. Inspección de Obra).
"""
from core.types import BaseSchema
from ninja import Field
import uuid
from typing import Optional
from decimal import Decimal
from datetime import date

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    VariablesFinancierasBasicasOut,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_schemas import (
    PerfilIngenieroOut,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    EspecialidadRevisionOut,
)

# =============================================================================
# Categoría Visitas — Entrada y Salida de cálculo
# =============================================================================
class LiquidacionPorCategoriaVisitasDatosIn(BaseSchema):
    cantidad_visitas: int = Field(
        ...,
        ge=1,
        le=9999,
        description="Cantidad de visitas solicitadas (1-9999)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Categoría derivada de la tarifa. Se acepta opcionalmente por compatibilidad legacy.",
    )


class LiquidacionPorCategoriaVisitasTarifaIn(BaseSchema):
    tarifa_visitas_id: uuid.UUID = Field(..., description="ID de la tarifa por categoría a aplicar")


class LiquidacionPorCategoriaVisitasIn(BaseSchema):
    """Esquema de entrada genérico para cualquier cálculo por Visitas."""
    datos: LiquidacionPorCategoriaVisitasDatosIn
    tarifa: LiquidacionPorCategoriaVisitasTarifaIn


class LiquidacionInspectorOut(BaseSchema):
    """Inspector asociado a una IO (sale dentro de liquidacion_tipo).

    Reutiliza PerfilIngenieroOut (schema de inspector) en lugar de duplicar
    los campos del perfil de ingeniero.
    """
    id: uuid.UUID
    inspector_id: uuid.UUID
    inspector_operacion_id: Optional[uuid.UUID] = None
    perfil_ingeniero: PerfilIngenieroOut
    especialidad_revision: Optional[EspecialidadRevisionOut] = None
    numero_registro: Optional[str] = None
    categoria: Optional[str] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class LiquidacionContinuidadVisitasOut(BaseSchema):
    """Esquema de salida de la fila de continuidad de visitas (si existe).

    `monto_acumulado` / `total_acumulado` = valor completo del trabajo.
    `subtotal_credito` / `total_credito` = crédito de la liquidación previa.
    La diferencia a cobrar es `liquidacion_general.sub_total` / `total`.

    Los montos se exponen como `float`, igual que `LiquidacionGeneralOutput`
    (misma convención monetaria de la API).
    """
    id: uuid.UUID
    liquidacion_previa_id: Optional[uuid.UUID] = None
    monto_acumulado: float = Field(0.0, description="Valor neto completo del trabajo")
    total_acumulado: float = Field(0.0, description="Valor bruto completo del trabajo")
    subtotal_credito: float = Field(0.0, description="Crédito neto de la previa")
    total_credito: float = Field(0.0, description="Crédito bruto de la previa")
    visitas_previas_totales: Optional[int] = None
    visitas_previas_pendientes: Optional[int] = None
    categoria_previa: Optional[str] = None
    observacion: Optional[str] = None


class LiquidacionPorCategoriaVisitasDatosOut(BaseSchema):
    """Esquema de salida que representa la tabla LiquidacionPorCategoriaVisitas."""
    id: uuid.UUID
    cantidad_visitas: int
    porcentaje_uit: Optional[Decimal] = None
    categoria: Optional[str] = None
    tarifa_aplicada_id: Optional[uuid.UUID] = None
    inspectores: list[LiquidacionInspectorOut] = []
    registros_pago: list["RegistroPagoInspectorOut"] = []
    continuidad: Optional[LiquidacionContinuidadVisitasOut] = None


class RegistroPagoInspectorOut(BaseSchema):
    """Schema de salida para RegistroPagoInspector."""
    id: uuid.UUID
    periodo: Optional[int] = None
    mes: Optional[int] = None
    inspecciones_pagadas: int
    fecha_registro: Optional[date] = None


# =============================================================================
# Categoría Visitas — Tarifas Vigentes
# =============================================================================
class TarifaVigenteVisitasDatos(BaseSchema):
    id: uuid.UUID
    costo_por_visita: Decimal
    categoria: str

class TarifasVigentesPorCategoriaVisitasOutputSchema(BaseSchema):
    """Devuelve las tarifas vigentes agrupables por categoría 1, 2, 3 o 4."""
    tarifas: list[TarifaVigenteVisitasDatos]


# =============================================================================
# Categoría Visitas — Cotizar
# =============================================================================
class CotizarPorCategoriaVisitasInputSchema(BaseSchema):
    liquidacion_especifica: LiquidacionPorCategoriaVisitasIn

class CotizarPorCategoriaVisitasTarifaOut(BaseSchema):
    id: uuid.UUID
    costo_por_visita: Decimal

class CotizarPorCategoriaVisitasDatosOutputSchema(BaseSchema):
    entrada: LiquidacionPorCategoriaVisitasIn
    tarifa: CotizarPorCategoriaVisitasTarifaOut
    variables_financieras: VariablesFinancierasBasicasOut

class CotizarPorCategoriaVisitasCalculoOutputSchema(BaseSchema):
    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal

class CotizarPorCategoriaVisitasOutputSchema(BaseSchema):
    datos: CotizarPorCategoriaVisitasDatosOutputSchema
    calculo: CotizarPorCategoriaVisitasCalculoOutputSchema
