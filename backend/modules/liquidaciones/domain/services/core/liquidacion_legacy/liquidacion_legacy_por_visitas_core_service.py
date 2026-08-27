"""
LiquidacionLegacyPorVisitasCoreService — ORM queries for legacy visitas-based liquidations.

PURE ORM — no business logic.
Handles: TarifaPorCategoriaVisitas, IGV, UIT resolved by fecha_registro.

Used by legacy flows for inspección de obra (visitas by category).
IGV and UIT require manual date filtering because their managers' vigente()
methods ignore the fecha parameter.
"""
from datetime import date

from django.db import models
from injector import inject

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class LiquidacionLegacyPorVisitasCoreService:
    """
    Core service for legacy Inspección de Obra (visitas) tariff queries resolved by date.

    All methods are pure ORM — no business logic, no conditionals.
    """

    @inject
    def __init__(self, tarifas_service: TarifasHistoricasCoreService) -> None:
        self._tarifas_service = tarifas_service

    def get_tarifa_visitas_por_fecha(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> list[TarifaPorCategoriaVisitas]:
        """
        Get all TarifaPorCategoriaVisitas records vigentes at the given fecha for a tipo_liquidacion.

        Resolution path:
        1. TarifaLiquidacionBase.objects.vigentes(fecha=fecha) filtered by tipo_liquidacion
        2. Join child TarifaPorCategoriaVisitas via ForeignKey tarifa_base

        Returns an empty list if no base tariff is vigentes at fecha.
        """
        tarifas_base = self._tarifas_service.get_tarifas_vigentes(tipo_liquidacion, fecha)
        if not tarifas_base:
            return []
        return self._tarifas_service.get_tarifas_categoria_visitas_por_base(
            [tb.id for tb in tarifas_base]
        )

    def get_igv_por_fecha(self, fecha: date) -> IGV | None:
        """
        Get the IGV vigente at the given fecha.

        IGV.objects.vigente() ignores the fecha parameter (only filters periodo_fin__isnull=True).
        Manual filter required: periodo_inicio__lte=fecha AND (periodo_fin__isnull OR periodo_fin__gte=fecha),
        ordered by periodo_inicio descending (most recent first).

        Returns None if no IGV covers the given fecha.
        """
        return (
            IGV.objects.filter(
                periodo_inicio__lte=fecha,
            )
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio")
            .first()
        )

    def get_tarifas_base_list(self, tipo_liquidacion: str, fecha: date) -> list:
        """
        Returns the raw list of TarifaLiquidacionBase vigentes at fecha for a tipo.
        Used by legacy orchestrators for overlap validation.
        """
        return self._tarifas_service.get_tarifas_vigentes(tipo_liquidacion, fecha)

    def get_uit_por_fecha(self, fecha: date) -> UIT | None:
        """
        Get the UIT vigente at the given fecha.

        UIT.objects.vigente() ignores the fecha parameter (only filters periodo_fin__isnull=True).
        Manual filter required: periodo_inicio__lte=fecha AND (periodo_fin__isnull OR periodo_fin__gte=fecha),
        ordered by periodo_inicio descending (most recent first).

        Returns None if no UIT covers the given fecha.
        """
        return (
            UIT.objects.filter(
                periodo_inicio__lte=fecha,
            )
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio")
            .first()
        )
