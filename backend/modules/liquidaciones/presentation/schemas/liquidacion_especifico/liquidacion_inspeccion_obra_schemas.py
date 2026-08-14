"""
Especifico Inspección de Obra schemas — Solo el payload final de primera-revisión.
"""
import uuid
from core.types import BaseSchema
from ninja import Field

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasIn,
    LiquidacionPorCategoriaVisitasDatosOut,
)


# =============================================================================
# POST /primera-revision — Único schema verdaderamente específico de Inspeccion de Obra
# =============================================================================
class LiquidacionInspeccionObraInput(BaseSchema):
    """Payload de entrada: Cabecera Genérica + cálculo de Visitas."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorCategoriaVisitasIn


class LiquidacionInspeccionObraOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo de Visitas."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput
    liquidacion_tipo: LiquidacionPorCategoriaVisitasDatosOut


# =============================================================================
# POST /nueva-liquidacion/primera-revision — IO desde liquidación previa
# Hereda proyecto/municipalidad/entidad de la liquidación previa.
# =============================================================================
class LiquidacionInspeccionObraNuevaRevisionDatosIn(BaseSchema):
    """Datos específicos de la revisión IO: cantidad de visitas y categoría."""
    cantidad_visitas: int = Field(..., description="Cantidad de visitas solicitadas")
    categoria: str = Field(..., description="Categoría seleccionada (ej. A, B, C)")


class LiquidacionInspeccionObraNuevaRevisionTarifaIn(BaseSchema):
    """Tarifa aplicada a la liquidación IO."""
    tarifa_visitas_id: uuid.UUID = Field(..., description="ID de la tarifa por categoría a aplicar")


class LiquidacionInspeccionObraNuevaRevisionEspecificaIn(BaseSchema):
    """
    Payload específico para IO primera-revision desde previa.
    Incluye inspector_id dentro de liquidacion_especifica (como lo solicitó el usuario).
    """
    datos: LiquidacionInspeccionObraNuevaRevisionDatosIn
    tarifa: LiquidacionInspeccionObraNuevaRevisionTarifaIn
    inspector_id: uuid.UUID = Field(..., description="ID del inspector asignado")


class LiquidacionInspeccionObraNuevaRevisionInput(BaseSchema):
    """
    Payload de entrada para crear una IO primera-revision heredando
    proyecto/municipalidad/entidad de una liquidación previa (Edificación o HU).
    """
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (Edificación o Habilitación Urbana)")
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn
