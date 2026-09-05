"""
Shared legacy input schema — `LiquidacionGeneralLegacyIn`.

Antes estaba duplicado 6 veces (una copia por tipo). Ahora vive aquí y los
6 schemas legacy lo importan. Incluye los campos opcionales de migración legacy.
"""
import uuid
from datetime import date
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    ProyectoCotizarSchema,
)


class LiquidacionGeneralLegacyIn(BaseSchema):
    """Inline liquidacion_general — mirrors LiquidacionGeneralRevisionIn fields + fecha_registro."""

    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    retencion: Optional[bool] = Field(False, description="Indica si la liquidación tiene retención")
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")
    fecha_registro: Optional[date] = Field(None, description="Fecha de registro histórica (para tarifas legacy)")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación de proyecto para liquidación (legacy)")
    descripcion_legacy: Optional[str] = Field(None, description="Descripción legacy del proyecto")
