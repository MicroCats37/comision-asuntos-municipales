"""
RH Inspector Candidatos results — DTOs internos para listado de candidatas del inspector.

Results heredan de pydantic.BaseModel (no BaseSchema).
Cumple con contrato 3C: domain/results/ = DTOs internos.
"""
from decimal import Decimal

from pydantic import BaseModel


class InspectorCandidataItemResult(BaseModel):
    """
    Item individual en el listado de candidatas del inspector para RH mensual.

    Representa una LiquidacionInspector asignada al inspector con saldo disponible.
    """
    liquidacion_inspector_id: str
    liquidacion_categoria_visitas_id: str
    liquidacion_general_id: str
    expediente: str
    numero_revision: int
    fecha_registro: str  # ISO date string
    inspector_nombre: str
    inspector_cip: str
    inspector_dni: str
    especialidad_nombre: str
    nombre_propietario: str  # from LiquidacionGeneral.proyecto.nombre_propietario
    cantidad_visitas: int  # inspecciones_programadas (from LiquidacionPorCategoriaVisitas)
    inspecciones_pagadas: int  # accumulated inspecciones_pagadas until previous period
    saldo_disponible: int  # cantidad_visitas - inspecciones_pagadas
    costo_por_inspeccion: Decimal  # sub_total / cantidad_visitas
    total_liquidacion: Decimal  # sub_total of LiquidacionGeneral
    sub_total_liquidacion: Decimal  # same as total_liquidacion


class InspectorCandidatosResult(BaseModel):
    """
    Resultado completo del listado de candidatas del inspector para RH mensual.
    """
    inspector_id: str
    inspector_nombre: str
    inspector_cip: str
    inspector_dni: str
    periodo: str
    candidatos: list[InspectorCandidataItemResult]
    total: int


class InspectorCandidatosPaginatedResult(BaseModel):
    """
    Resultado paginado del listado de candidatas del inspector para RH mensual.
    """
    inspector_id: str
    inspector_nombre: str
    inspector_cip: str
    inspector_dni: str
    periodo: str
    items: list[InspectorCandidataItemResult]
    total: int
    page: int
    page_size: int
    total_pages: int
