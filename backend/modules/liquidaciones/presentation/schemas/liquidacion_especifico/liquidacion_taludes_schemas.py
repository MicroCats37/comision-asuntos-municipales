"""
Presentation schemas for Taludes (PorcentajeObra).

Input: 2 wrappers (general + especifica)
Output: 3 wrappers (general + especifica=identidad + tipo=cálculo)
"""
import uuid
from decimal import Decimal
from typing import Optional, List
from core.types import BaseSchema
from ninja import Field
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraTarifaIn,
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
    EspecialidadOut,
)


class LiquidacionTipoOutput(BaseSchema):
    """Output de identidad: solo id + numero."""
    id: uuid.UUID
    numero: Optional[int] = Field(None, description="Número secuencial correlativo de la especialidad")


class LiquidacionTaludesInput(BaseSchema):
    """Input: 2 wrappers."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionTaludesOutput(BaseSchema):
    """Output: 3 wrappers."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # identidad
    liquidacion_tipo: LiquidacionPorcentajeObraDatosOut  # cálculo


class LiquidacionTaludesCotizarInput(BaseSchema):
    """
    Input for /cotizar endpoint.

    Only liquidacion_especifica is needed (no liquidacion_general).
    """
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionTaludesCotizarTarifaOut(BaseSchema):
    """Tarifa applied in cotizacion."""
    tarifa_id: uuid.UUID
    porcentaje_aplicado: Decimal
    especialidad_id: uuid.UUID


class LiquidacionTaludesCotizarDetalleOut(BaseSchema):
    """Detalle of cotizacion."""
    tarifa_id: Optional[uuid.UUID] = None
    especialidad: Optional[EspecialidadOut] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal


class LiquidacionTaludesCotizarOutput(BaseSchema):
    """Output for /cotizar endpoint."""
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[uuid.UUID] = None
    detalles: List[LiquidacionTaludesCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal


class LiquidacionTaludesRelacionadaInput(BaseSchema):
    """
    Input para /relacionada — crea una nueva liquidacion con numero_revision=1
    vinculada a una liquidacion previa existente.

    Usa la misma estructura que primera-revision (full input) más el
    liquidacion_previa_id para establecer la relación de grupo.
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionTaludesNuevaRevisionInput(BaseSchema):
    """
    Input para /nueva-revision — crea la siguiente revisión impar (1→3→5)
    vinculada a una liquidación previa existente.
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: "LiquidacionTaludesGeneralNuevaRevisionIn"
    liquidacion_especifica: "LiquidacionTaludesEspecificaNuevaRevisionIn"


class LiquidacionTaludesGeneralNuevaRevisionIn(BaseSchema):
    """Input reducido para nueva revisión — sin municipalidad/proyecto."""
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal")


class LiquidacionTaludesEspecificaNuevaRevisionIn(BaseSchema):
    """Input específico para nueva revisión — tarifas; valor_declarado se hereda de la previa."""
    tarifas: List[LiquidacionPorcentajeObraTarifaIn]
