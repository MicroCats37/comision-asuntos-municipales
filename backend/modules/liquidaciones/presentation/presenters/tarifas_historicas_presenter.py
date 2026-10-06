"""
TarifasHistoricasPresenter — Presenter for historical tariff and derecho endpoints.

@staticmethod only. Maps Domain Results -> Schemas. No ORM access.
"""
import math
from typing import List, Union
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
    # General endpoint discriminated schemas
    TarifaPorcentajeItemSchema,
    TarifaM2ItemSchema,
    TarifaVisitasItemSchema,
    TarifaPorcentajeGeneralSchema,
    TarifaM2GeneralSchema,
    TarifaVisitasGeneralSchema,
)
from core.pagination import PaginatedData


# Constants for tipo_tarifa discriminator values
TIPO_TARIFA_PORCENTAJE = "porcentaje"
TIPO_TARIFA_M2 = "m2"
TIPO_TARIFA_VISITAS = "visitas"


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
                        porcentaje_liquidacion=float(d.porcentaje_liquidacion),
                    )
                    for d in r.tarifas_porcentaje
                ],
                tarifa_m2=TarifaM2DetalleSchema(
                    id=r.tarifa_m2.id,
                    costo_por_m2=float(r.tarifa_m2.costo_por_m2),
                ) if r.tarifa_m2 else None,
                tarifas_visitas=[
                    TarifaVisitasDetalleSchema(
                        id=v.id,
                        categoria=v.categoria,
                        porcentaje_uit=float(v.porcentaje_uit),
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

    @staticmethod
    def present_tarifas_generales(
        resultados: List[TarifaHistoricaPeriodoResult],
    ) -> List[Union[
        TarifaPorcentajeItemSchema,
        TarifaM2ItemSchema,
        TarifaVisitasItemSchema,
    ]]:
        """
        Maps list of TarifaHistoricaPeriodoResult to discriminated union items
        for the general /liquidaciones/tarifas endpoint.

        Each item has a tipo_tarifa discriminator and only its relevant detail key.
        No empty arrays or irrelevant fields are returned.
        """
        items: List[Union[
            TarifaPorcentajeItemSchema,
            TarifaM2ItemSchema,
            TarifaVisitasItemSchema,
        ]] = []

        for r in resultados:
            if r.tarifas_porcentaje:
                for tarifa in r.tarifas_porcentaje:
                    items.append(TarifaPorcentajeItemSchema(
                        tipo_tarifa=TIPO_TARIFA_PORCENTAJE,
                        tipo_liquidacion=r.tipo_liquidacion,
                        periodo_inicio=r.periodo_inicio,
                        periodo_fin=r.periodo_fin,
                        tarifa_porcentaje=TarifaPorcentajeGeneralSchema(
                            id=tarifa.id,
                            especialidad=tarifa.especialidad_nombre,
                            porcentaje=tarifa.porcentaje_liquidacion,
                        ),
                    ))
            elif r.tarifa_m2:
                items.append(TarifaM2ItemSchema(
                    tipo_tarifa=TIPO_TARIFA_M2,
                    tipo_liquidacion=r.tipo_liquidacion,
                    periodo_inicio=r.periodo_inicio,
                    periodo_fin=r.periodo_fin,
                    tarifa_m2=TarifaM2GeneralSchema(
                        id=r.tarifa_m2.id,
                        monto=r.tarifa_m2.costo_por_m2,
                    ),
                ))
            elif r.tarifas_visitas:
                for tarifa in r.tarifas_visitas:
                    items.append(TarifaVisitasItemSchema(
                        tipo_tarifa=TIPO_TARIFA_VISITAS,
                        tipo_liquidacion=r.tipo_liquidacion,
                        periodo_inicio=r.periodo_inicio,
                        periodo_fin=r.periodo_fin,
                        tarifa_visitas=TarifaVisitasGeneralSchema(
                            id=tarifa.id,
                            categoria=tarifa.categoria,
                            porcentaje_uit=tarifa.porcentaje_uit,
                        ),
                    ))

        return items


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
                    derecho_minimo=float(r.derecho_minimo) if r.derecho_minimo is not None else None,
                    derecho_maximo=float(r.derecho_maximo) if r.derecho_maximo is not None else None,
                    porcentaje_minimo_uit=float(r.porcentaje_minimo_uit) if r.porcentaje_minimo_uit is not None else None,
                    periodo_inicio=r.periodo_inicio,
                    periodo_fin=r.periodo_fin,
                )
                for r in resultados
            ]
        )
