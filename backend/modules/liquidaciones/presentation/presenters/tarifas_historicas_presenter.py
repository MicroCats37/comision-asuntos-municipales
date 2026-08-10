"""
TarifasHistoricasPresenter — Presenter for historical tariff and derecho endpoints.

@staticmethod only. Maps Domain Results -> Schemas. No ORM access.
"""
import math
from typing import List
from datetime import date
from uuid import UUID

from modules.liquidaciones.domain.results.tarifas_historicas_results import (
    TarifaHistoricaPeriodoResult,
    TarifaPorcentajeObraDetalleResult,
    TarifaM2Result,
    TarifaVisitasResult,
    DerechoHistoricoResult,
)
from modules.liquidaciones.presentation.schemas.tarifas_historicas_schemas import (
    TarifaHistoricaPeriodoSchema,
    TarifaPorcentajeObraDetalleSchema,
    TarifaM2DetalleSchema,
    TarifaVisitasDetalleSchema,
    TarifasHistoricasResponseSchema,
    DerechoHistoricoSchema,
    DerechosHistoricosResponseSchema,
)
from core.pagination import PaginatedData


class TarifasHistoricasPresenter:
    """Presenter for historical tariff queries."""

    @staticmethod
    def present_tarifas_historicas(
        resultados: List[TarifaHistoricaPeriodoResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[TarifaHistoricaPeriodoSchema]:
        """
        Maps list of TarifaHistoricaPeriodoResult to PaginatedData[TarifaHistoricaPeriodoSchema].
        """
        items: List[TarifaHistoricaPeriodoSchema] = []
        for r in resultados:
            periodo = TarifaHistoricaPeriodoSchema(
                id=r.id,
                tipo_liquidacion=r.tipo_liquidacion,
                periodo_inicio=r.periodo_inicio,
                periodo_fin=r.periodo_fin,
                tarifas_porcentaje=[
                    TarifaPorcentajeObraDetalleSchema(
                        id=d.id,
                        especialidad_id=d.especialidad_id,
                        especialidad_nombre=d.especialidad_nombre,
                        porcentaje_liquidacion=d.porcentaje_liquidacion,
                    )
                    for d in r.tarifas_porcentaje
                ],
                tarifa_m2=TarifaM2DetalleSchema(
                    id=r.tarifa_m2.id,
                    costo_por_m2=r.tarifa_m2.costo_por_m2,
                ) if r.tarifa_m2 else None,
                tarifas_visitas=[
                    TarifaVisitasDetalleSchema(
                        id=v.id,
                        categoria=v.categoria,
                        porcentaje_uit=v.porcentaje_uit,
                    )
                    for v in r.tarifas_visitas
                ],
            )
            items.append(periodo)

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class DerechosHistoricosPresenter:
    """Presenter for historical derecho queries."""

    @staticmethod
    def present_derechos_historicos(
        resultados: List[DerechoHistoricoResult],
    ) -> DerechosHistoricosResponseSchema:
        """
        Maps list of DerechoHistoricoResult to DerechosHistoricosResponseSchema.
        """
        return DerechosHistoricosResponseSchema(
            derechos=[
                DerechoHistoricoSchema(
                    id=r.id,
                    derecho_minimo=r.derecho_minimo,
                    derecho_maximo=r.derecho_maximo,
                    porcentaje_minimo_uit=r.porcentaje_minimo_uit,
                    periodo_inicio=r.periodo_inicio,
                    periodo_fin=r.periodo_fin,
                )
                for r in resultados
            ]
        )