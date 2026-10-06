from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.results.inspector.inspector_result import (
    PerfilIngenieroResult,
)


class RegistroPagoResult(BaseModel):
    """Domain DTO for RegistroPagoInspector (nested in LiquidacionPorCategoriaVisitas)."""
    id: str
    periodo: Optional[int] = None
    mes: Optional[int] = None
    inspecciones_pagadas: int
    fecha_registro: Optional[date] = None


class EspecialidadRevisionResult(BaseModel):
    """Domain DTO for EspecialidadRevision (nested en inspector de liquidación)."""
    id: str
    nombre: str


class LiquidacionInspectorResult(BaseModel):
    """Inspector asociado a una liquidación de Inspección de Obra.

    Reutiliza PerfilIngenieroResult (dominio de inspector) en lugar de
    duplicar los campos del perfil de ingeniero.
    """
    id: str
    inspector_id: str
    inspector_operacion_id: Optional[str] = None
    perfil_ingeniero: PerfilIngenieroResult
    especialidad_revision: Optional[EspecialidadRevisionResult] = None
    numero_registro: Optional[str] = None
    categoria: Optional[str] = None
    periodo: Optional[int] = None
    mes: Optional[int] = None
    dictamen_revision: Optional[str] = None
    fecha_presentacion: Optional[str] = None
    fecha_revision: Optional[str] = None


class LiquidacionVisitasResult(BaseModel):
    id: str
    cantidad_visitas: int
    porcentaje_uit: Optional[Decimal] = None
    categoria: Optional[str] = None
    tarifa_aplicada_id: Optional[str] = None
    inspectores: list[LiquidacionInspectorResult] = []
    registros_pago: list[RegistroPagoResult] = []
