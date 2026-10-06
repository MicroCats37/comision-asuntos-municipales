"""
Inspector Batch Schemas — API contracts for batch operations on LiquidacionInspector.

Used for PATCH /liquidaciones/{id}/inspectores.
"""
import uuid
from typing import Optional

from core.types import BaseSchema


class LiquidacionInspectorCreateIn(BaseSchema):
    """Input item para crear una asociación LiquidacionInspector."""
    inspector_id: uuid.UUID
    inspector_operacion_id: uuid.UUID


class LiquidacionInspectorUpdateIn(BaseSchema):
    """Input item para actualizar metadata de una LiquidacionInspector."""
    inspector_id: uuid.UUID


class LiquidacionInspectorDeleteIn(BaseSchema):
    """Input item para eliminar una asociación LiquidacionInspector."""
    inspector_id: uuid.UUID


class LiquidacionInspectorBatchIn(BaseSchema):
    """Batch payload agrupado para PATCH /liquidaciones/{id}/inspectores."""
    create: list[LiquidacionInspectorCreateIn] = []
    update: list[LiquidacionInspectorUpdateIn] = []
    delete: list[LiquidacionInspectorDeleteIn] = []


class LiquidacionInspectorOut(BaseSchema):
    """Output schema para una asociación LiquidacionInspector."""
    id: uuid.UUID
    liquidacion_id: uuid.UUID
    inspector_id: uuid.UUID
    inspector_operacion_id: Optional[uuid.UUID] = None


class LiquidacionInspectorBatchOut(BaseSchema):
    """Output schema agrupado para PATCH /liquidaciones/{id}/inspectores."""
    created: list[LiquidacionInspectorOut] = []
    updated: list[LiquidacionInspectorOut] = []
    deleted: list[str] = []
