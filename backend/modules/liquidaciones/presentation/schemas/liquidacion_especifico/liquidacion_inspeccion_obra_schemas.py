"""
Especifico Inspección de Obra schemas — Solo el payload final de primera-revisión.
"""
import uuid
from typing import Optional, Union
from core.types import BaseSchema
from ninja import Field

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasDatosOut,
)


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
    """
    Datos específicos de la revisión IO: cantidad de visitas y categoría.

    categoria is nullable — for the legacy/manual path (CATEGORIA=0), no valid
    tariff category exists, so categoria is stored as null along with a null tarifa.
    Normal UI path should still enforce a valid categoria.
    """
    cantidad_visitas: int = Field(..., description="Cantidad de visitas solicitadas")
    categoria: Optional[str] = Field(
        None,
        description="Categoría seleccionada (ej. A, B, C). Null for legacy CATEGORIA=0 records.",
    )


class LiquidacionInspeccionObraNuevaRevisionTarifaIn(BaseSchema):
    """
    Tarifa aplicada a la liquidación IO.

    tarifa_visitas_id is nullable — for the legacy/manual path (CATEGORIA=0 or
    unmatched tariff), no valid tariff exists, so the record is created with a
    null FK and modo_calculo=MANUAL.
    Uses Union to preserve Pydantic string→UUID coercion for string inputs.
    Normal UI path should still enforce a valid tarifa_visitas_id.
    """
    tarifa_visitas_id: Union[uuid.UUID, str, None] = Field(
        None,
        description="ID de la tarifa por categoría a aplicar. Null for legacy CATEGORIA=0 records.",
    )


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
    proyecto/municipalidad/entidad de una liquidación previa (Edificación o Habilitación Urbana).
    """
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (Edificación o Habilitación Urbana)")
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")
