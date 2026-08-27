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
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarResult,
    RHInspectorMensualListItemResult,
)
from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
    InspectorCandidatosResult,
)
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    RHDelegadoCotizarResult,
    RHDelegadoMensualListItemResult,
    RHDelegadoMensualDetalleResult,
    RHDelegadoMensualTotalesResult,
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
    RHInspectorCotizarItemOut,
    RHInspectorTotalesOut,
    RHInspectorCotizarOut,
    InspectorCandidataItemOut,
    InspectorCandidatosOut,
    RHDelegadoCotizarItemOut,
    RHDelegadoTotalesOut,
    RHDelegadoCotizarOut,
    RHDelegadoMensualDetalleOut,
    RHDelegadoMensualTotalesOut,
    RHDelegadoMensualListItemOut,
    RHInspectorMensualDetalleOut,
    RHInspectorMensualTotalesOut,
    RHInspectorMensualListItemOut,
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

    # ── RH Inspector Mensual ─────────────────────────────────────────────────────

    @staticmethod
    def present_rh_inspector_mensual(
        result: RHInspectorCotizarResult,
    ) -> RHInspectorCotizarOut:
        """
        Transforma un RHInspectorCotizarResult → RHInspectorCotizarOut.

        Args:
            result: Result del orchestrator con detalle de cotización mensual.

        Returns:
            RHInspectorCotizarOut listo para success_response().
        """
        return RHInspectorCotizarOut(
            inspector=InspectorMinimalOut(
                id=uuid.UUID(result.inspector.id),
                nombre_completo=result.inspector.nombre_completo,
                cip=result.inspector.cip,
                dni=result.inspector.dni,
            ),
            periodo=result.periodo,
            items=[
                RHInspectorCotizarItemOut(
                    exp_liqui=i.exp_liqui,
                    liquidacion_inspector_id=uuid.UUID(i.liquidacion_inspector_id),
                    liquidacion_categoria_visitas_id=uuid.UUID(i.liquidacion_categoria_visitas_id),
                    nombre_propietario=i.nombre_propietario,
                    importe_bruto=i.importe_bruto,
                    inspecciones_programadas=i.inspecciones_programadas,
                    inspecciones_liquidadas=i.inspecciones_liquidadas,
                    inspecciones_pagadas_hasta_mes_anterior=i.inspecciones_pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=i.costo_por_inspeccion,
                    monto_contribuido=i.monto_contribuido,
                    saldo_disponible=i.saldo_disponible,
                    saldo_restante=i.saldo_restante,
                )
                for i in result.items
            ],
            totales=RHInspectorTotalesOut(
                sub_total=result.totales.sub_total,
                descuento=result.totales.descuento,
                honorarios=result.totales.honorarios,
                tasa_descuento_aplicada=result.totales.tasa_descuento_aplicada,
            ),
            escala_descuento_id=uuid.UUID(result.escala_descuento_id),
        )

    @staticmethod
    def present_inspector_candidatos(
        result: InspectorCandidatosResult,
    ) -> InspectorCandidatosOut:
        """
        Transforma un InspectorCandidatosResult → InspectorCandidatosOut.

        Args:
            result: Result del orchestrator con lista de candidatas.

        Returns:
            InspectorCandidatosOut listo para success_response().
        """
        return InspectorCandidatosOut(
            inspector_id=uuid.UUID(result.inspector_id),
            inspector_nombre=result.inspector_nombre,
            inspector_cip=result.inspector_cip,
            inspector_dni=result.inspector_dni,
            periodo=result.periodo,
            candidatos=[
                InspectorCandidataItemOut(
                    liquidacion_inspector_id=uuid.UUID(c.liquidacion_inspector_id),
                    liquidacion_categoria_visitas_id=uuid.UUID(c.liquidacion_categoria_visitas_id),
                    liquidacion_general_id=uuid.UUID(c.liquidacion_general_id),
                    expediente=c.expediente,
                    numero_revision=c.numero_revision,
                    fecha_registro=c.fecha_registro,
                    inspector_nombre=c.inspector_nombre,
                    inspector_cip=c.inspector_cip,
                    inspector_dni=c.inspector_dni,
                    especialidad_nombre=c.especialidad_nombre,
                    nombre_propietario=c.nombre_propietario,
                    cantidad_visitas=c.cantidad_visitas,
                    inspecciones_pagadas=c.inspecciones_pagadas,
                    saldo_disponible=c.saldo_disponible,
                    costo_por_inspeccion=c.costo_por_inspeccion,
                    total_liquidacion=c.total_liquidacion,
                    sub_total_liquidacion=c.sub_total_liquidacion,
                )
                for c in result.candidatos
            ],
            total=result.total,
        )

    # ── RH Delegado Mensual ─────────────────────────────────────────────────────

    @staticmethod
    def present_rh_delegado_mensual(
        result: RHDelegadoCotizarResult,
    ) -> RHDelegadoCotizarOut:
        """
        Transforma un RHDelegadoCotizarResult → RHDelegadoCotizarOut.

        Args:
            result: Result del orchestrator con detalle de cotización mensual.

        Returns:
            RHDelegadoCotizarOut listo para success_response().
        """
        return RHDelegadoCotizarOut(
            delegado=DelegadoMinimalOut(
                id=uuid.UUID(result.delegado.id),
                nombre_completo=result.delegado.nombre_completo,
                cip=result.delegado.cip,
                dni=result.delegado.dni,
            ),
            periodo=result.periodo,
            items=[
                RHDelegadoCotizarItemOut(
                    exp_liqui=i.exp_liqui,
                    liquidacion_delegado_id=uuid.UUID(i.liquidacion_delegado_id) if i.liquidacion_delegado_id else None,
                    imp_bruto=i.imp_bruto,
                    fecha_revision=i.fecha_revision,
                    numero_revision=i.numero_revision,
                    total_liquidacion=i.total_liquidacion,
                    sub_total_liquidacion=i.sub_total_liquidacion,
                    numero_rh=i.numero_rh,
                    renta_cip=i.renta_cip,
                    aporte_codemu=i.aporte_codemu,
                    fondo_comun=i.fondo_comun,
                    neto_honorario=i.neto_honorario,
                )
                for i in result.items
            ],
            totales=RHDelegadoTotalesOut(
                sub_total=result.totales.sub_total,
                renta_cip=result.totales.renta_cip,
                aporte_codemu=result.totales.aporte_codemu,
                fondo_comun=result.totales.fondo_comun,
                neto_honorario=result.totales.neto_honorario,
            ),
        )

    @staticmethod
    def present_rh_mensuales_delegado_list(
        domain_results: list[RHDelegadoMensualListItemResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[RHDelegadoMensualListItemOut]:
        """
        Transforma lista de RHDelegadoMensualListItemResult → PaginatedData[RHDelegadoMensualListItemOut].

        Args:
            domain_results: Lista de resultados del orchestrator.
            total: Total de registros en la query base (sin paginar).
            page: Página actual.
            page_size: Tamaño de página usado.

        Returns:
            PaginatedData lista para success_response().
        """
        items: list[RHDelegadoMensualListItemOut] = [
            FinanzasPresenter._map_rh_mensual_delegado_out(r) for r in domain_results
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def _map_rh_mensual_delegado_out(
        r: RHDelegadoMensualListItemResult,
    ) -> RHDelegadoMensualListItemOut:
        """Mapea un RHDelegadoMensualListItemResult → RHDelegadoMensualListItemOut."""
        return RHDelegadoMensualListItemOut(
            id=uuid.UUID(r.id),
            periodo=r.periodo,
            fecha_registro=datetime.fromisoformat(r.fecha_registro) if r.fecha_registro else datetime.min,
            delegado=DelegadoMinimalOut(
                id=uuid.UUID(r.delegado.id),
                cip=r.delegado.cip,
                dni=r.delegado.dni,
                nombre_completo=r.delegado.nombre_completo,
            ),
            totales=RHDelegadoMensualTotalesOut(
                sub_total=r.totales.sub_total,
                renta_cip=r.totales.renta_cip,
                aporte_codemu=r.totales.aporte_codemu,
                fondo_comun=r.totales.fondo_comun,
                neto_honorario=r.totales.neto_honorario,
            ),
            detalles=[
                RHDelegadoMensualDetalleOut(
                    expediente=d.expediente,
                    imp_bruto=d.imp_bruto,
                )
                for d in r.detalles
            ],
        )

    # ── RH Inspector Mensual — Listado ───────────────────────────────────────────

    @staticmethod
    def present_rh_mensuales_inspector_list(
        domain_results: list[RHInspectorMensualListItemResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[RHInspectorMensualListItemOut]:
        """
        Transforma lista de RHInspectorMensualListItemResult → PaginatedData[RHInspectorMensualListItemOut].

        Args:
            domain_results: Lista de resultados del orchestrator.
            total: Total de registros en la query base (sin paginar).
            page: Página actual.
            page_size: Tamaño de página usado.

        Returns:
            PaginatedData lista para success_response().
        """
        items: list[RHInspectorMensualListItemOut] = [
            FinanzasPresenter._map_rh_mensual_inspector_out(r) for r in domain_results
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def _map_rh_mensual_inspector_out(
        r: RHInspectorMensualListItemResult,
    ) -> RHInspectorMensualListItemOut:
        """Mapea un RHInspectorMensualListItemResult → RHInspectorMensualListItemOut."""
        return RHInspectorMensualListItemOut(
            id=uuid.UUID(r.id),
            periodo=r.periodo,
            fecha_registro=datetime.fromisoformat(r.fecha_registro) if r.fecha_registro else datetime.min,
            inspector=InspectorMinimalOut(
                id=uuid.UUID(r.inspector.id),
                cip=r.inspector.cip,
                dni=r.inspector.dni,
                nombre_completo=r.inspector.nombre_completo,
            ),
            totales=RHInspectorMensualTotalesOut(
                inspecciones_programadas=r.totales.inspecciones_programadas,
                inspecciones_liquidadas=r.totales.inspecciones_liquidadas,
                inspecciones_pagadas_hasta_mes_anterior=r.totales.inspecciones_pagadas_hasta_mes_anterior,
                saldo_restante=r.totales.saldo_restante,
                sub_total=r.totales.sub_total,
                descuento=r.totales.descuento,
                honorarios=r.totales.honorarios,
                tasa_descuento_aplicada=r.totales.tasa_descuento_aplicada,
            ),
            detalles=[
                RHInspectorMensualDetalleOut(
                    expediente=d.expediente,
                    nombre_propietario=d.nombre_propietario,
                    importe_bruto=d.importe_bruto,
                    inspecciones_programadas=d.inspecciones_programadas,
                    inspecciones_liquidadas=d.inspecciones_liquidadas,
                    inspecciones_pagadas_hasta_mes_anterior=d.inspecciones_pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=d.costo_por_inspeccion,
                    monto_contribuido=d.monto_contribuido,
                    saldo_restante=d.saldo_restante,
                )
                for d in r.detalles
            ],
        )
