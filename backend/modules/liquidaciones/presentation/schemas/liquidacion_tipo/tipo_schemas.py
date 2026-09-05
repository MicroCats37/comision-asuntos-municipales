"""
Tipo presentation schemas — Estructuras de cálculo por tipo (M2, Visitas, Porcentaje).

Contiene los schemas de entrada, salida, cotización y tarifas vigentes
reutilizables por cualquier especialidad que use el mismo tipo de cálculo.
"""
from core.types import BaseSchema
from ninja import Field
from pydantic import ConfigDict
from decimal import Decimal
import uuid
from typing import Optional

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    VariablesFinancierasNulasOut,
)

# =============================================================================
# Identidad del Tipo — Wrapper de auto-número
# =============================================================================
class LiquidacionTipoOutput(BaseSchema):
    id: uuid.UUID = Field(..., description="ID de la liquidación del tipo específico")
    numero: Optional[int] = Field(None, description="Número secuencial correlativo de la especialidad")


# =============================================================================
# Metro Cuadrado (M2) — Entrada y Salida de cálculo
# =============================================================================
class LiquidacionPorMetroCuadradoDatosIn(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    area_solicitada: Decimal = Field(..., description="Área solicitada en metros cuadrados")

class LiquidacionPorMetroCuadradoTarifaIn(BaseSchema):
    tarifa_m2_id: uuid.UUID = Field(..., description="ID de la tarifa M2 a aplicar")

class LiquidacionPorMetroCuadradoIn(BaseSchema):
    """Esquema de entrada genérico para cualquier cálculo M2."""
    datos: LiquidacionPorMetroCuadradoDatosIn
    tarifa: LiquidacionPorMetroCuadradoTarifaIn

class LiquidacionPorMetroCuadradoDatosOut(BaseSchema):
    """Esquema de salida que representa la tabla LiquidacionPorMetroCuadrado."""
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    id: uuid.UUID
    area_m2: Decimal
    costo_por_m2: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Decimal
    tarifa_aplicada_id: uuid.UUID
    derecho_aplicado_id: uuid.UUID


# =============================================================================
# Metro Cuadrado (M2) — Tarifas Vigentes
# =============================================================================
class TarifaVigentePorMetroCuadradoDatos(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    id: uuid.UUID
    costo_por_m2: Decimal

class TarifaVigentePorMetroCuadradoWrapper(BaseSchema):
    datos: TarifaVigentePorMetroCuadradoDatos

class DerechoVigentePorMetroCuadradoDatos(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    id: uuid.UUID
    derecho_minimo: Decimal
    derecho_maximo: Decimal

class DerechoVigentePorMetroCuadradoWrapper(BaseSchema):
    datos: DerechoVigentePorMetroCuadradoDatos

class TarifasVigentesPorMetroCuadradoOutputSchema(BaseSchema):
    tarifa_vigente: TarifaVigentePorMetroCuadradoWrapper
    derecho_vigente: DerechoVigentePorMetroCuadradoWrapper


# =============================================================================
# Metro Cuadrado (M2) — Cotizar
# =============================================================================
class CotizarPorMetroCuadradoInputSchema(BaseSchema):
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn

class CotizarPorMetroCuadradoTarifaOut(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    id: uuid.UUID
    costo_por_m2: Decimal

class CotizarPorMetroCuadradoDerechoOut(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    id: uuid.UUID
    derecho_minimo: Decimal
    derecho_maximo: Decimal

class CotizarPorMetroCuadradoDatosOutputSchema(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    entrada: LiquidacionPorMetroCuadradoIn
    tarifa: CotizarPorMetroCuadradoTarifaOut
    derecho: CotizarPorMetroCuadradoDerechoOut
    variables_financieras: VariablesFinancierasNulasOut

class CotizarPorMetroCuadradoCalculoOutputSchema(BaseSchema):
    model_config = ConfigDict(ser_json_decimal_to_float=True)

    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal

class CotizarPorMetroCuadradoOutputSchema(BaseSchema):
    datos: CotizarPorMetroCuadradoDatosOutputSchema
    calculo: CotizarPorMetroCuadradoCalculoOutputSchema

