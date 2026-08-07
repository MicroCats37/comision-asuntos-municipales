"""
Domain schemas — DTOs internos para servicios de Habilitacion Urbana.
"""
import uuid
from pydantic import BaseModel
from typing import Optional


class ProyectoResultData(BaseModel):
    """Datos del proyecto en el resultado."""
    id: uuid.UUID
    denominacion: str
    entidad_razon_social: Optional[str] = None
    entidad_tipo_documento: Optional[str] = None
    entidad_numero_documento: Optional[str] = None
    nombre_propietario: str
    direccion: Optional[str] = None
    urbanizacion: Optional[str] = None


class LiquidacionGeneralResultData(BaseModel):
    """Datos de la liquidacion general en el resultado."""
    id: uuid.UUID
    municipalidad_id: uuid.UUID
    usuario_creador_id: uuid.UUID
    fecha_registro: str
    estado: str
    expediente: str
    observacion: Optional[str] = None
    retencion: bool
    numero_revision: int
    sub_total: float
    total: float
    igv_id: Optional[uuid.UUID] = None
    uit_id: Optional[uuid.UUID] = None
    proyecto: ProyectoResultData


class LiquidacionTipoResultData(BaseModel):
    """Datos del tipo de liquidacion en el resultado."""
    id: uuid.UUID
    numero: int


class LiquidacionEspecificaDatosResultData(BaseModel):
    """Datos especificos de calculo M2 en el resultado."""
    area_m2: float
    costo_por_m2: float
    minimo: float
    maximo: Optional[float] = None


class LiquidacionEspecificaTarifaResultData(BaseModel):
    """Datos de tarifa M2 en el resultado."""
    tarifa_m2_id: uuid.UUID


class LiquidacionEspecificaResultData(BaseModel):
    """Datos especificos de habilitacion urbana en el resultado."""
    datos: LiquidacionEspecificaDatosResultData
    tarifa: LiquidacionEspecificaTarifaResultData


class LiquidacionHabilitacionUrbanaResult(BaseModel):
    """Resultado completo de una liquidacion de habilitacion urbana."""
    liquidacion_general: LiquidacionGeneralResultData
    liquidacion_tipo: LiquidacionTipoResultData
    liquidacion_especifica: LiquidacionEspecificaResultData
