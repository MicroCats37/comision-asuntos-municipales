"""
TarifasHistoricasCoreService — ORM queries for historical tariffs.

Pure ORM. No business logic.
"""
from typing import List, Optional, Tuple
from datetime import date

from django.db.models import Q, QuerySet

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
)


class TarifasHistoricasCoreService:
    """
    Core service for querying historical tariff records.
    """

    def get_tarifas_historicas(
        self,
        tipo_liquidacion: str,
        fecha_desde: date,
        fecha_hasta: date,
        page: int,
        page_size: int,
    ) -> Tuple[List[TarifaLiquidacionBase], int]:
        """
        Get historical tariff bases for a tipo_liquidacion within a date range.
        
        Returns (list of TarifaLiquidacionBase, total_count).
        """
        qs = TarifaLiquidacionBase.objects.filter(
            tipo_liquidacion__codigo=tipo_liquidacion,
        ).filter(
            periodo_inicio__lte=fecha_hasta,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha_desde)
        ).order_by("periodo_inicio")

        total = qs.count()
        offset = (page - 1) * page_size
        items = list(qs[offset:offset + page_size])
        return items, total

    def get_tarifas_porcentaje_obra_por_base(
        self,
        tarifa_base_ids: List[str],
    ) -> List[TarifaPorcentajeObra]:
        """
        Get all TarifaPorcentajeObra records for the given TarifaLiquidacionBase IDs.
        Returns list ordered by especialidad.
        """
        return list(
            TarifaPorcentajeObra.objects.filter(
                tarifa_base_id__in=tarifa_base_ids
            ).select_related("tarifa_base", "especialidad").order_by("especialidad__nombre")
        )

    def get_tarifa_m2_por_base(
        self,
        tarifa_base_id: str,
    ) -> Optional[TarifaPorMetroCuadrado]:
        """
        Get TarifaPorMetroCuadrado for a single TarifaLiquidacionBase (OneToOne).
        """
        try:
            return TarifaPorMetroCuadrado.objects.select_related("tarifa_base").get(
                tarifa_base_id=tarifa_base_id
            )
        except TarifaPorMetroCuadrado.DoesNotExist:
            return None

    def get_tarifas_categoria_visitas_por_base(
        self,
        tarifa_base_ids: List[str],
    ) -> List[TarifaPorCategoriaVisitas]:
        """
        Get all TarifaPorCategoriaVisitas records for the given TarifaLiquidacionBase IDs.
        Multiple categories can exist per base period.
        """
        return list(
            TarifaPorCategoriaVisitas.objects.filter(
                tarifa_base_id__in=tarifa_base_ids
            ).select_related("tarifa_base").order_by("categoria_visitas")
        )

    def get_derechos_porcentaje_historicos(
        self,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> List[DerechoPorcentajeObra]:
        """
        Get historical DerechoPorcentajeObra records within a date range.
        """
        return list(
            DerechoPorcentajeObra.objects.filter(
                periodo_inicio__lte=fecha_hasta,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha_desde)
            ).order_by("periodo_inicio")
        )

    def get_derechos_m2_historicos(
        self,
        fecha_desde: date,
        fecha_hasta: date,
    ) -> List[DerechoPorMetroCuadrado]:
        """
        Get historical DerechoPorMetroCuadrado records within a date range.
        """
        return list(
            DerechoPorMetroCuadrado.objects.filter(
                periodo_inicio__lte=fecha_hasta,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha_desde)
            ).order_by("periodo_inicio")
        )