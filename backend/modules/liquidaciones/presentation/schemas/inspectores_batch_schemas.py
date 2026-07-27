"""Presentation schemas para batch de LiquidacionInspector."""

import uuid
from datetime import date
from typing import Optional

from ninja import Field
from pydantic import ConfigDict

from core.types import BaseSchema


class LiquidacionInspectorCreateIn(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    inspector_id: uuid.UUID = Field(..., description="UUID del inspector a asociar")
    periodo: Optional[str] = Field(None, max_length=100)
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None


class LiquidacionInspectorUpdateIn(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    periodo: Optional[str] = Field(None, max_length=100)
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None


class LiquidacionInspectorUpdateItemIn(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    inspector_id: uuid.UUID
    body: LiquidacionInspectorUpdateIn


class LiquidacionInspectorDeleteIn(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    inspector_id: uuid.UUID


class LiquidacionInspectorBatchIn(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    create: list[LiquidacionInspectorCreateIn] = Field(default_factory=list)
    update: list[LiquidacionInspectorUpdateItemIn] = Field(default_factory=list)
    delete: list[LiquidacionInspectorDeleteIn] = Field(default_factory=list)


class InspectorBasicOut(BaseSchema):
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo_liquidacion: Optional[str] = None
    categoria: Optional[int] = None
    numero_registro: Optional[str] = None
    vigencia: Optional[date] = None


class LiquidacionInspectorOut(BaseSchema):
    model_config = ConfigDict(extra="allow")

    id: uuid.UUID
    inspector_id: uuid.UUID
    periodo: Optional[str] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[date] = None
    fecha_revision: Optional[date] = None
    inspector: Optional[InspectorBasicOut] = None


class LiquidacionInspectorBatchOut(BaseSchema):
    model_config = ConfigDict(extra="allow")

    created: list[LiquidacionInspectorOut] = Field(default_factory=list)
    updated: list[LiquidacionInspectorOut] = Field(default_factory=list)
    deleted: list[str] = Field(default_factory=list)
