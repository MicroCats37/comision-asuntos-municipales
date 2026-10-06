"""
Presentation schemas for Edificaciones (PorcentajeObra).

Input: 2 wrappers (general + especifica)
Output: 3 wrappers (general + especifica=identidad + tipo=cálculo)
"""
import uuid
from decimal import Decimal
from typing import Optional, List
from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
    ContactoInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
    LiquidacionPorcentajeObraTarifaIn,
    EspecialidadOut,
)


class LiquidacionTipoOutput(BaseSchema):
    """Output de identidad: solo id + numero."""
    id: uuid.UUID
    numero: Optional[int] = Field(None, description="Número secuencial correlativo de la especialidad")


class LiquidacionEdificacionesInput(BaseSchema):
    """Input: 2 wrappers."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionEdificacionesOutput(BaseSchema):
    """Output: 3 wrappers."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # identidad
    liquidacion_tipo: LiquidacionPorcentajeObraDatosOut  # cálculo


class LiquidacionEdificacionesCotizarInput(BaseSchema):
    """
    Input for /cotizar endpoint.
    
    Only liquidacion_especifica is needed (no liquidacion_general).
    """
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionEdificacionesCotizarTarifaOut(BaseSchema):
    """Tarifa applied in cotizacion."""
    tarifa_id: uuid.UUID
    porcentaje_aplicado: Decimal
    especialidad_id: uuid.UUID


class LiquidacionEdificacionesCotizarDetalleOut(BaseSchema):
    """Detalle of cotizacion."""
    tarifa_id: Optional[uuid.UUID] = None
    especialidad: Optional[EspecialidadOut] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal


class LiquidacionGeneralNuevaRevisionIn(BaseSchema):
    """Input reducido para nueva revisión — solo campos editables (sin municipalidad/proyecto)."""
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    retencion: bool = Field(False, description="Indica si la liquidación tiene retención")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional, hereda de la previa si no se provee)")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")


class LiquidacionEspecificaNuevaRevisionIn(BaseSchema):
    """Input específico para nueva revisión — tarifas + tipo_tramite (sin datos, se hereda de la previa)."""
    tipo_tramite: Optional[str] = Field(
        None,
        description="Tipo de trámite de edificaciones (ej. OBRA_NUEVA, AMPLIACION, etc.)",
    )
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = Field(
        ...,
        description="Tarifas seleccionadas. NO puede estar vacío y deben estar vigentes.",
    )


class LiquidacionEdificacionesNuevaRevisionInput(BaseSchema):
    """Input para /nueva-revision — schema específico reducido.

    Hereda de la liquidación previa: proyecto, municipalidad, valor_declarado.
    Solo se editan: expediente, observacion, retencion, contacto y tarifas.
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralNuevaRevisionIn
    liquidacion_especifica: LiquidacionEspecificaNuevaRevisionIn


class LiquidacionEdificacionesRelacionadaInput(BaseSchema):
    """
    Input para /relacionada — crea una nueva liquidacion con numero_revision=1
    vinculada a una liquidacion previa existente.

    Usa la misma estructura que primera-revision (full input) más el
    liquidacion_previa_id para establecer la relación de grupo.
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn


class LiquidacionEdificacionesCotizarOutput(BaseSchema):
    """Output for /cotizar endpoint."""
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[uuid.UUID] = None
    detalles: List[LiquidacionEdificacionesCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal
