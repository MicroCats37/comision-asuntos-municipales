"""
Presentation schemas for PorcentajeObra motor.

Input: User sends tarifas[] (can be empty for auto-fill mode).
Output: 3 wrappers with detalles[] nested in liquidacion_tipo.
"""
import uuid
from decimal import Decimal
from typing import List, Optional
from core.types import BaseSchema


class LiquidacionPorcentajeObraDatosIn(BaseSchema):
    """Datos básicos de entrada."""
    valor_declarado: Decimal


class LiquidacionPorcentajeObraTarifaIn(BaseSchema):
    """
    Tarifa seleccionada por el usuario con especialidad explícita.

    With tarifa-unica-especialidades: the same tarifa can be sent multiple
    times with different especialidad_id values (one entry per specialty).
    Backend validates each entry by tariff ID + vigencia.
    """
    tarifa_porcentaje_obra_id: uuid.UUID
    especialidad_id: uuid.UUID


class LiquidacionPorcentajeObraIn(BaseSchema):
    """
    Wrapper Input del motor PorcentajeObra.
    
    Si `tarifas` está vacío, el backend auto-rellena con todas las vigentes.
    Si tiene elementos, se validan explícitamente.
    """
    datos: LiquidacionPorcentajeObraDatosIn
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = []


class LiquidacionPorcentajeObraDetalleOut(BaseSchema):
    """Detalle de una liquidación porcentual aplicada a una especialidad."""
    id: uuid.UUID
    tarifa_aplicada_id: uuid.UUID
    especialidad_id: uuid.UUID
    porcentaje_aplicado: Decimal
    subtotal: Decimal


class LiquidacionPorcentajeObraDatosOut(BaseSchema):
    """
    Wrapper Output del motor PorcentajeObra.
    
    Contiene los detalles anidados (1-N por especialidad).
    """
    id: uuid.UUID
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal  # SUM de tarifas aplicadas
    tipo_tramite: Optional[str] = None  # NULL por ahora
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: uuid.UUID
    detalles: List[LiquidacionPorcentajeObraDetalleOut]
