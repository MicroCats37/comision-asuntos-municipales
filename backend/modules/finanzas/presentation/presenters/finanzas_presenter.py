"""
FinanzasPresenter — transforma resultados de dominio a esquema HTTP.

Cumple con el contrato de arquitectura (sección 3A: presenters).
Solo @staticmethod/@classmethod, PROHIBIDO tocar BD.
"""
import math
import uuid
from datetime import datetime
from decimal import Decimal

from core.pagination import PaginatedData
from modules.finanzas.domain.schemas import VariablesVigentesResult
from modules.finanzas.domain.results.recibo_honorario_result import (
    ReciboHonorarioDelegadoResult,
    ReciboHonorarioInspectorResult,
)
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    VariablesFinancierasOut,
    ReciboHonorarioDelegadoOut,
    ReciboHonorarioInspectorOut,
    LiquidacionGeneralMinimalOut,
    DelegadoMinimalOut,
    InspectorMinimalOut,
    EspecialidadMinimalOut,
    TipoLiquidacionMinimalOut,
    ReciboHonorarioCalculoOut,
    ReciboHonorarioInspectorCalculoOut,
    LiquidacionEspecificaMinimalOut,
)


class FinanzasPresenter:
    """
    Presenter para transformación de resultados de dominio a esquemas HTTP.

    Responsabilidad: transformar explícitamente Results (dominio)
    → Schemas Out (HTTP simplificada para frontend).
    """

    @staticmethod
    def present_variables_vigentes(domain_result: VariablesVigentesResult) -> VariablesFinancierasOut:
        """
        Transforma VariablesVigentesResult (dominio) a VariablesFinancierasOut (HTTP).

        Mapeo:
        - igv_valor → igv_valor
        - igv_periodo_inicio → igv_periodo_inicio (ISO string)
        - uit_valor → uit_valor
        - uit_periodo_inicio → uit_periodo_inicio (ISO string)

        Args:
            domain_result: VariablesVigentesResult del orchestrator

        Returns:
            VariablesFinancierasOut listo para success_response()
        """
        return VariablesFinancierasOut(
            igv_valor=domain_result.igv_valor,
            igv_periodo_inicio=domain_result.igv_periodo_inicio.isoformat(),
            uit_valor=domain_result.uit_valor,
            uit_periodo_inicio=domain_result.uit_periodo_inicio.isoformat(),
        )

    @staticmethod
    def present_recibo(domain_result: ReciboHonorarioDelegadoResult) -> ReciboHonorarioDelegadoOut:
        """
        Transforma un ReciboHonorarioDelegadoResult → ReciboHonorarioDelegadoOut.

        Mismo schema que el listado (homogéneo): incluye los resúmenes anidados
        de liquidacion_general, delegado y especialidad.

        Args:
            domain_result: Result del orchestrator (con anidados).

        Returns:
            ReciboHonorarioDelegadoOut listo para success_response().
        """
        return FinanzasPresenter._map_recibo_out(domain_result)

    @staticmethod
    def _map_recibo_out(r: ReciboHonorarioDelegadoResult) -> ReciboHonorarioDelegadoOut:
        """Mapea un ReciboHonorarioDelegadoResult → ReciboHonorarioDelegadoOut."""
        lg = r.liquidacion_general
        return ReciboHonorarioDelegadoOut(
            id=uuid.UUID(r.id),
            liquidacion_delegado_id=r.liquidacion_delegado_id,
            liquidacion_general=LiquidacionGeneralMinimalOut(
                id=uuid.UUID(lg.id),
                expediente=lg.expediente,
                numero_revision=lg.numero_revision,
                sub_total=Decimal(str(lg.sub_total)),
                total=Decimal(str(lg.total)),
                fecha_registro=datetime.fromisoformat(lg.fecha_registro) if lg.fecha_registro else datetime.min,
                tipo_liquidacion=TipoLiquidacionMinimalOut(
                    codigo=lg.tipo_liquidacion.codigo,
                    nombre=lg.tipo_liquidacion.nombre,
                ),
                municipalidad_nombre=lg.municipalidad_nombre,
                proyecto_denominacion=lg.proyecto_denominacion,
            ),
            delegado=DelegadoMinimalOut(
                id=uuid.UUID(r.delegado.id),
                cip=r.delegado.cip,
                dni=r.delegado.dni,
                nombre_completo=r.delegado.nombre_completo,
            ),
            especialidad=EspecialidadMinimalOut(
                id=uuid.UUID(r.especialidad.id),
                codigo=r.especialidad.codigo,
                nombre=r.especialidad.nombre,
            ),
            calculo=ReciboHonorarioCalculoOut(
                sub_total=Decimal(str(r.calculo.sub_total)),
                imp_bruto=Decimal(str(r.calculo.imp_bruto)),
                renta_cip=Decimal(str(r.calculo.renta_cip)),
                aporte_codemu=Decimal(str(r.calculo.aporte_codemu)),
                fondo_comun=Decimal(str(r.calculo.fondo_comun)),
                neto_honorario=Decimal(str(r.calculo.neto_honorario)),
                honorario=Decimal(str(r.calculo.honorario)),
            ),
            liquidacion_especifica=LiquidacionEspecificaMinimalOut(
                id=uuid.UUID(r.liquidacion_especifica.id),
                numero=r.liquidacion_especifica.numero,
            ),
            created_at=r.created_at,
        )

    @staticmethod
    def present_recibos_list(
        domain_results: list[ReciboHonorarioDelegadoResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[ReciboHonorarioDelegadoOut]:
        """
        Transforma lista de ReciboHonorarioDelegadoResult → PaginatedData[ReciboHonorarioDelegadoOut].

        Args:
            domain_results: Lista de resultados del orchestrator.
            total: Total de registros en la query base (sin paginar).
            page: Página actual.
            page_size: Tamaño de página usado.

        Returns:
            PaginatedData lista para success_response().
        """
        items: list[ReciboHonorarioDelegadoOut] = [
            FinanzasPresenter._map_recibo_out(r) for r in domain_results
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ── ReciboHonorarioInspector ────────────────────────────────────────────────

    @staticmethod
    def present_recibo_inspector(
        domain_result: ReciboHonorarioInspectorResult,
    ) -> ReciboHonorarioInspectorOut:
        """
        Transforma un ReciboHonorarioInspectorResult → ReciboHonorarioInspectorOut.

        Mismo schema que el listado (homogéneo): incluye los resúmenes anidados
        de liquidacion_general, inspector y especialidad.

        Args:
            domain_result: Result del orchestrator (con anidados).

        Returns:
            ReciboHonorarioInspectorOut listo para success_response().
        """
        return FinanzasPresenter._map_recibo_inspector_out(domain_result)

    @staticmethod
    def _map_recibo_inspector_out(
        r: ReciboHonorarioInspectorResult,
    ) -> ReciboHonorarioInspectorOut:
        """Mapea un ReciboHonorarioInspectorResult → ReciboHonorarioInspectorOut."""
        lg = r.liquidacion_general
        return ReciboHonorarioInspectorOut(
            id=uuid.UUID(r.id),
            liquidacion_inspector_id=r.liquidacion_inspector_id,
            liquidacion_general=LiquidacionGeneralMinimalOut(
                id=uuid.UUID(lg.id),
                expediente=lg.expediente,
                numero_revision=lg.numero_revision,
                sub_total=Decimal(str(lg.sub_total)),
                total=Decimal(str(lg.total)),
                fecha_registro=datetime.fromisoformat(lg.fecha_registro) if lg.fecha_registro else datetime.min,
                tipo_liquidacion=TipoLiquidacionMinimalOut(
                    codigo=lg.tipo_liquidacion.codigo,
                    nombre=lg.tipo_liquidacion.nombre,
                ),
                municipalidad_nombre=lg.municipalidad_nombre,
                proyecto_denominacion=lg.proyecto_denominacion,
            ),
            liquidacion_especifica=LiquidacionEspecificaMinimalOut(
                id=uuid.UUID(r.liquidacion_especifica.id),
                numero=r.liquidacion_especifica.numero,
            ),
            inspector=InspectorMinimalOut(
                id=uuid.UUID(r.inspector.id),
                cip=r.inspector.cip,
                dni=r.inspector.dni,
                nombre_completo=r.inspector.nombre_completo,
            ),
            especialidad=EspecialidadMinimalOut(
                id=uuid.UUID(r.especialidad.id),
                codigo=r.especialidad.codigo,
                nombre=r.especialidad.nombre,
            ),
            calculo=ReciboHonorarioInspectorCalculoOut(
                inspecciones_programadas=r.calculo.inspecciones_programadas,
                costo_por_inspeccion=Decimal(str(r.calculo.costo_por_inspeccion)),
                inspecciones_mes=r.calculo.inspecciones_mes,
                monto_bruto=Decimal(str(r.calculo.monto_bruto)),
                inspecciones_pagadas=r.calculo.inspecciones_pagadas,
                saldo_inspecciones=r.calculo.saldo_inspecciones,
                sub_total=Decimal(str(r.calculo.sub_total)),
                tasa_descuento_aplicada=Decimal(str(r.calculo.tasa_descuento_aplicada)),
                descuento=Decimal(str(r.calculo.descuento)),
                honorarios=Decimal(str(r.calculo.honorarios)),
            ),
            created_at=r.created_at,
        )

    @staticmethod
    def present_recibos_inspectores_list(
        domain_results: list[ReciboHonorarioInspectorResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[ReciboHonorarioInspectorOut]:
        """
        Transforma lista de ReciboHonorarioInspectorResult → PaginatedData.

        Args:
            domain_results: Lista de resultados del orchestrator.
            total: Total de registros en la query base (sin paginar).
            page: Página actual.
            page_size: Tamaño de página usado.

        Returns:
            PaginatedData lista para success_response().
        """
        items: list[ReciboHonorarioInspectorOut] = [
            FinanzasPresenter._map_recibo_inspector_out(r)
            for r in domain_results
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
