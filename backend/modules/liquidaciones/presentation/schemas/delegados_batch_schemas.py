"""
Presentation schemas — Esquemas HTTP para Batch de LiquidacionDelegado.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.

Endpoint: PATCH /liquidaciones/{liquidacion_id}/delegados
Patrón: BatchPayload con create/update/delete usando delegado_id como clave.
"""
import uuid
from datetime import date
from typing import Optional

from ninja import Field
from pydantic import ConfigDict

from core.types import BaseSchema
from modules.liquidaciones.domain.constants import DictamenRevision


# =============================================================================
# Schemas de Entrada (Input)
# =============================================================================


class LiquidacionDelegadoCreateIn(BaseSchema):
    """
    Payload para crear una asociación LiquidacionDelegado.

    Args:
        delegado_id: UUID del delegado a asociar (requerido).
        periodo: Periodo de asignación (opcional).
        dictamen_revision: Dictamen de revisión: CONFORME, NO_CONFORME,
                          PENDIENTE, AP_OB (opcional).
        fecha_presentacion: Fecha de presentación (opcional).
        fecha_revision: Fecha de revisión (opcional).
    """
    model_config = ConfigDict(extra="forbid")

    delegado_id: uuid.UUID = Field(..., description="UUID del delegado a asociar")
    periodo: Optional[str] = Field(
        None,
        max_length=100,
        description="Periodo de asignación del delegado",
    )
    dictamen_revision: Optional[str] = Field(
        None,
        description="Dictamen de revisión: CONFORME, NO_CONFORME, PENDIENTE, AP_OB",
    )
    fecha_presentacion: Optional[date] = Field(
        None,
        description="Fecha de presentación del delegado",
    )
    fecha_revision: Optional[date] = Field(
        None,
        description="Fecha de revisión del delegado",
    )


class LiquidacionDelegadoUpdateIn(BaseSchema):
    """
    Payload para actualizar metadata de una asociación LiquidacionDelegado existente.

    Todos los campos son opcionales — solo se actualizan los proporcionados.

    Args:
        periodo: Periodo de asignación (opcional).
        dictamen_revision: Dictamen de revisión: CONFORME, NO_CONFORME,
                          PENDIENTE, AP_OB (opcional).
        fecha_presentacion: Fecha de presentación (opcional).
        fecha_revision: Fecha de revisión (opcional).
    """
    model_config = ConfigDict(extra="forbid")

    periodo: Optional[str] = Field(
        None,
        max_length=100,
        description="Periodo de asignación del delegado",
    )
    dictamen_revision: Optional[str] = Field(
        None,
        description="Dictamen de revisión: CONFORME, NO_CONFORME, PENDIENTE, AP_OB",
    )
    fecha_presentacion: Optional[date] = Field(
        None,
        description="Fecha de presentación del delegado",
    )
    fecha_revision: Optional[date] = Field(
        None,
        description="Fecha de revisión del delegado",
    )


class LiquidacionDelegadoUpdateItemIn(BaseSchema):
    """
    Item individual para operación de actualización en batch.

    Usa delegado_id como clave de identificación (único por liquidacion).

    Args:
        delegado_id: UUID del delegado cuya asociación se actualiza.
        body: Campos a actualizar (todos opcionales).
    """
    model_config = ConfigDict(extra="forbid")

    delegado_id: uuid.UUID = Field(..., description="UUID del delegado a actualizar")
    body: LiquidacionDelegadoUpdateIn = Field(
        ...,
        description="Campos a actualizar en la asociación",
    )


class LiquidacionDelegadoDeleteIn(BaseSchema):
    """
    Item individual para operación de eliminación en batch.

    Usa delegado_id como clave de identificación (único por liquidacion).

    Args:
        delegado_id: UUID del delegado cuya asociación se eliminará.
    """
    model_config = ConfigDict(extra="forbid")

    delegado_id: uuid.UUID = Field(..., description="UUID del delegado a desvincular")


class LiquidacionDelegadoBatchIn(BaseSchema):
    """
    Payload batch para crear, actualizar y eliminar delegados de una liquidación.

    Endpoint: PATCH /liquidaciones/{liquidacion_id}/delegados

    Args:
        create: Lista de delegados a crear (opcional, puede estar vacía).
        update: Lista de delegados a actualizar (opcional, puede estar vacía).
        delete: Lista de delegado_ids a desvincular (opcional, puede estar vacía).

    Validaciones del orquestador:
        - Todos los delegado_id en create/update/delete deben ser únicos en el payload.
        - El delegado debe existir y estar activo.
        - El delegado debe estar asignado a la municipalidad de la liquidación.
        - La categoría del delegado debe coincidir con el tipo_liquidacion.
        - Para update/delete, la asociación debe existir.
    """
    model_config = ConfigDict(extra="forbid")

    create: list[LiquidacionDelegadoCreateIn] = Field(
        default_factory=list,
        description="Lista de delegados a crear para esta liquidación",
    )
    update: list[LiquidacionDelegadoUpdateItemIn] = Field(
        default_factory=list,
        description="Lista de delegados a actualizar en esta liquidación",
    )
    delete: list[LiquidacionDelegadoDeleteIn] = Field(
        default_factory=list,
        description="Lista de delegados a desvincular de esta liquidación",
    )


# =============================================================================
# Schemas de Salida (Output)
# =============================================================================


class DelegadoBasicOut(BaseSchema):
    """
    Información básica del delegado para respuesta.

    Anidado dentro de LiquidacionDelegadoOut.
    """
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID = Field(..., description="ID del delegado")
    perfil_ingeniero_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del perfil de ingeniero",
    )
    perfil_ingeniero_nombres: Optional[str] = Field(
        None,
        description="Nombres del ingeniero",
    )
    perfil_ingeniero_apellidos: Optional[str] = Field(
        None,
        description="Apellidos del ingeniero",
    )
    perfil_ingeniero_cip: Optional[str] = Field(
        None,
        description="Número de CIP del ingeniero",
    )
    especialidad_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la especialidad",
    )
    especialidad_nombre: Optional[str] = Field(
        None,
        description="Nombre de la especialidad",
    )
    tipo: Optional[str] = Field(
        None,
        description="Tipo de delegado: titular o alterno",
    )


class LiquidacionDelegadoOut(BaseSchema):
    """
    Schema de respuesta para una asociación LiquidacionDelegado.

    Incluye tanto la metadata de la asociación (periodo, dictamen, fechas)
    como la información del delegado asociado.

    Args:
        id: UUID de la asociación LiquidacionDelegado.
        delegado_id: UUID del delegado.
        periodo: Periodo de asignación.
        dictamen_revision: Dictamen de revisión.
        fecha_presentacion: Fecha de presentación.
        fecha_revision: Fecha de revisión.
        delegado: Información básica del delegado (anidado).
    """
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID = Field(..., description="ID de la asociación LiquidacionDelegado")
    delegado_id: uuid.UUID = Field(..., description="UUID del delegado")
    periodo: Optional[str] = Field(None, description="Periodo de asignación")
    dictamen_revision: Optional[str] = Field(
        None,
        description="Dictamen de revisión",
    )
    fecha_presentacion: Optional[date] = Field(
        None,
        description="Fecha de presentación",
    )
    fecha_revision: Optional[date] = Field(
        None,
        description="Fecha de revisión",
    )
    delegado: Optional[DelegadoBasicOut] = Field(
        None,
        description="Información del delegado asociado",
    )


class LiquidacionDelegadoBatchOut(BaseSchema):
    """
    Respuesta batch con resultados agrupados de operaciones create/update/delete.

    Endpoint: PATCH /liquidaciones/{liquidacion_id}/delegados

    Args:
        created: Lista de asociaciones creadas exitosamente.
        updated: Lista de asociaciones actualizadas exitosamente.
        deleted: Lista de delegado_ids desvinculados exitosamente.
    """
    model_config = ConfigDict(extra="allow")

    created: list[LiquidacionDelegadoOut] = Field(
        default_factory=list,
        description="Delegados creados exitosamente",
    )
    updated: list[LiquidacionDelegadoOut] = Field(
        default_factory=list,
        description="Delegados actualizados exitosamente",
    )
    deleted: list[str] = Field(
        default_factory=list,
        description="Delegado IDs desvinculados exitosamente",
    )
