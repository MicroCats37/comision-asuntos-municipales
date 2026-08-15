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
)
from modules.finanzas.presentation.schemas.finanzas_schemas import (
    VariablesFinancierasOut,
    ReciboHonorarioDelegadoOut,
    LiquidacionGeneralMinimalOut,
    DelegadoMinimalOut,
    EspecialidadMinimalOut,
    TipoLiquidacionMinimalOut,
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
            sub_total=Decimal(str(r.sub_total)),
            imp_bruto=Decimal(str(r.imp_bruto)),
            renta_cip=Decimal(str(r.renta_cip)),
            aporte_codemu=Decimal(str(r.aporte_codemu)),
            fondo_comun=Decimal(str(r.fondo_comun)),
            neto_honorario=Decimal(str(r.neto_honorario)),
            honorario=Decimal(str(r.honorario)),
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
