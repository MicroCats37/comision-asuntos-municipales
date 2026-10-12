"""
LiquidacionLegacyPorVisitasCoreService — consultas ORM para liquidaciones legacy basadas en visitas.

ORM PURO — sin lógica de negocio.
Maneja: TarifaPorCategoriaVisitas, IGV, UIT resueltos por fecha_registro.

Usado por flujos legacy para inspección de obra (visitas por categoría).
IGV y UIT requieren filtrado manual por fecha porque los métodos vigente()
de sus managers ignoran el parámetro fecha.
"""
import functools
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

    @staticmethod
    @functools.cache
    def get_uit_map_by_year() -> dict:
        """
        UIT map keyed by year: {year: {"id": str, "valor": int}}.

        Cached at process level — first call queries the DB, subsequent calls
        return the cached dict. Avoids per-row DB queries during legacy import.
        """
        return {
            uit.periodo_inicio.year: {"id": str(uit.id), "valor": int(uit.valor)}
            for uit in UIT.objects.all()
        }

    @staticmethod
    def get_uit_by_id(uit_id: str):
        """Resolve a UIT id (string) to its valor via the in-memory map."""
        for data in LiquidacionLegacyPorVisitasCoreService.get_uit_map_by_year().values():
            if data["id"] == uit_id:
                return data["valor"]
        return None

    @staticmethod
    def ensure_uit_for_legacy(uit_valor: int, fecha: date | None = None) -> "UIT":
        """
        Ensure a UIT record exists in BD with the given valor for the given fecha,
        creating one if missing. Used by legacy orchestrators when caller passes
        `uit_valor_override` for a historical value not yet in the vigentes map.

        Strategy:
        1. Look for an existing UIT record with same valor that covers `fecha`
           (periodo_inicio <= fecha <= periodo_fin or no periodo_fin).
        2. If found, return it.
        3. Otherwise, return any existing UIT with the same valor (most recent).
        4. Otherwise, create a new UIT record with periodo_inicio = max(fecha, today - 1y)
           and periodo_fin = None (vigente forever for legacy purposes).

        Returns a UIT ORM instance whose pk is set (either existing or just created).
        """
        from modules.finanzas.domain.models.impuestos import UIT
        from datetime import date as _date

        target_fecha = fecha or _date.today()

        # 1. Existing UIT with same valor covering target_fecha
        existente = (
            UIT.objects.filter(valor=uit_valor, periodo_inicio__lte=target_fecha)
            .filter(models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=target_fecha))
            .order_by("-periodo_inicio")
            .first()
        )
        if existente is not None:
            return existente

        # 2. Any existing UIT with same valor (regardless of fecha)
        existente = (
            UIT.objects.filter(valor=uit_valor)
            .order_by("-periodo_inicio")
            .first()
        )
        if existente is not None:
            return existente

        # 3. Create new UIT record for legacy use
        periodo_inicio = target_fecha.replace(day=1)
        nuevo = UIT.objects.create(
            valor=uit_valor,
            periodo_inicio=periodo_inicio,
            periodo_fin=None,
        )
        return nuevo

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
