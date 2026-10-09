"""
Especifico Inspección de Obra schemas — payloads de primera-revisión.
"""
import uuid
from typing import Optional, Union
from core.types import BaseSchema
from ninja import Field

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
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
    Payload específico para IO primera-revision (con o sin previa).

    Para sin previa (nueva-liquidacion): inspector_operacion_id es OBLIGATORIO.
    La especialidad_revision se deriva de InspectorOperacion.especialidad_revision.
    El inspector se deriva de InspectorOperacion.inspector.

    Para con previa (relacionada): inspector_operacion_id es OBLIGATORIO.
    Se valida que InspectorOperacion.tipo_liquidacion coincida con la previa.

    inspector_id es OPCIONAL — se usa solo para cross-validación con
    InspectorOperacion.inspector_id cuando ambos están presentes.
    tipo_liquidacion ya no va en el input — se deriva de InspectorOperacion.
    """
    datos: LiquidacionInspeccionObraNuevaRevisionDatosIn
    tarifa: LiquidacionInspeccionObraNuevaRevisionTarifaIn
    inspector_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del inspector asignado. Opcional — se valida contra inspector_operacion si ambos presentes.",
    )
    inspector_operacion_id: uuid.UUID = Field(
        ...,
        description="ID de la InspectorOperacion del inspector seleccionado. "
                    "Obligatorio para ambos flujos (nueva y relacionada). "
                    "Se usa para derivar inspector, especialidad_revision y tipo_liquidacion. "
                    "Obtenido del endpoint /seleccionables.",
    )


class LiquidacionInspeccionObraNuevaLiquidacionInput(BaseSchema):
    """
    Payload de entrada para crear una IO primera-revision SIN liquidación previa.
    Entidad y Proyecto se crean desde cero a partir de los datos del usuario.
    No requiere liquidacion_previa_id.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn = Field(
        ..., description="Datos generales con proyecto, entidad y municipalidad desde entrada del usuario"
    )
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn = Field(
        ..., description="Datos específicos IO: datos, tarifa e inspector_id"
    )


class LiquidacionInspeccionObraNuevaRevisionInput(BaseSchema):
    """
    Payload de entrada para crear una IO primera-revision heredando
    proyecto/municipalidad/entidad de una liquidación previa (Edificación o Habilitación Urbana).
    """
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (Edificación o Habilitación Urbana)")
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")
