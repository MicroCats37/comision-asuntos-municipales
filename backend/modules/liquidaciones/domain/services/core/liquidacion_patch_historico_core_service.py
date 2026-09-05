"""
LiquidacionPatchHistoricoCoreService — Shared historical tariff resolution for PATCH recalculation.

PURE ORM — no business logic, no mutations.

Resolves IGV, UIT, tarifas, and derechos to their values that were vigente
at a given fecha (typically LiquidacionGeneral.fecha_registro.date()).

Key rules:
- IGV/UIT managers' vigente() ignores fecha — use manual filter instead.
- VigenciaModel.vigentes(fecha=fecha) handles other records correctly.
- Overlapping periods: use NEWEST at fecha = order_by("-periodo_inicio").first()
- NO silent fallback to current values — raise BusinessError if not found.
"""
from datetime import date
from typing import Optional

from django.db import models

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from core.exceptions import BusinessError


class NoIGVVigenteError(BusinessError):
    """Raised when no IGV record is vigente at the given fecha."""

    def __init__(self, fecha: date):
        super().__init__(
            f"No existe IGV vigente para la fecha {fecha}. "
            f"No se puede recalcular sin valores históricos."
        )


class NoUITVigenteError(BusinessError):
    """Raised when no UIT record is vigente at the given fecha."""

    def __init__(self, fecha: date):
        super().__init__(
            f"No existe UIT vigente para la fecha {fecha}. "
            f"No se puede recalcular sin valores históricos."
        )


class NoTarifaVigenteError(BusinessError):
    """Raised when no TarifaLiquidacionBase is vigente at the given fecha."""

    def __init__(self, tipo_liquidacion: str, fecha: date):
        super().__init__(
            f"No existe tarifa base vigente para {tipo_liquidacion} en la fecha {fecha}. "
            f"No se puede recalcular sin valores históricos."
        )


class NoDerechoVigenteError(BusinessError):
    """Raised when no DerechoPorcentajeObra/DerechoPorMetroCuadrado is vigente."""

    def __init__(self, tipo: str, fecha: date):
        super().__init__(
            f"No existe derecho ({tipo}) vigente para la fecha {fecha}. "
            f"No se puede recalcular sin valores históricos."
        )


class LiquidacionPatchHistoricoCoreService:
    """
    Shared service for resolving financial variables (IGV, UIT, tarifas, derechos)
    by their historical values vigente at a specific fecha.

    All methods are PURE READ-ONLY ORM — no business logic, no mutations.
    Used by PATCH recalculation endpoints to ensure historical accuracy.

    Usage:
        service = LiquidacionPatchHistoricoCoreService()
        fecha = liquidacion.liquidacion_general.fecha_registro.date()
        igv = service.get_igv_por_fecha(fecha)        # raises if not found
        uit = service.get_uit_por_fecha(fecha)        # raises if not found
        tarifas_base = service.get_tarifa_base_vigente(tipo_liq, fecha)  # list, raises if empty
    """

    def __init__(self) -> None:
        self._tarifas_service = TarifasHistoricasCoreService()

    # ── IGV ─────────────────────────────────────────────────────────────────

    def get_igv_por_fecha(self, fecha: date) -> IGV:
        """
        Get the IGV vigente at the given fecha.

        IGV.objects.vigente() ignores fecha — manual filter required.
        Uses the legacy pattern: periodo_inicio__lte=fecha AND
        (periodo_fin__isnull OR periodo_fin__gte=fecha), ordered by
        periodo_inicio DESC, first() = newest at fecha.

        Raises:
            NoIGVVigenteError: If no IGV covers the given fecha.

        Returns:
            IGV instance vigente at fecha.
        """
        # Clear default ordering (IGV model has Meta.ordering) and use pk as
        # tiebreaker for deterministic results when periods overlap.
        result = (
            IGV.objects.filter(
                periodo_inicio__lte=fecha,
            )
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio", "pk")
            .first()
        )
        if result is None:
            raise NoIGVVigenteError(fecha)
        return result

    # ── UIT ─────────────────────────────────────────────────────────────────

    def get_uit_por_fecha(self, fecha: date) -> UIT:
        """
        Get the UIT vigente at the given fecha.

        UIT.objects.vigente() ignores fecha — manual filter required.
        Same pattern as get_igv_por_fecha.

        Raises:
            NoUITVigenteError: If no UIT covers the given fecha.

        Returns:
            UIT instance vigente at fecha.
        """
        # Clear default ordering (UIT model has Meta.ordering) and use pk as
        # tiebreaker for deterministic results when periods overlap.
        result = (
            UIT.objects.filter(
                periodo_inicio__lte=fecha,
            )
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio", "pk")
            .first()
        )
        if result is None:
            raise NoUITVigenteError(fecha)
        return result

    # ── TarifaLiquidacionBase ────────────────────────────────────────────────

    def get_tarifa_base_vigente(self, tipo_liquidacion: str, fecha: date) -> TarifaLiquidacionBase:
        """
        Get the TarifaLiquidacionBase vigente at the given fecha for a tipo_liquidacion.

        Uses VigenciaModel.vigentes(fecha=fecha) which correctly filters by date.
        Returns the NEWEST overlapping record (order_by("-periodo_inicio").first()).

        Raises:
            NoTarifaVigenteError: If no base tariff is vigente at fecha.

        Returns:
            TarifaLiquidacionBase instance vigente at fecha.
        """
        qs = (
            TarifaLiquidacionBase.objects
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .vigentes(fecha=fecha)
            .order_by("-periodo_inicio")
        )
        result = qs.first()
        if result is None:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)
        return result

    def get_tarifa_base_vigente_list(
        self, tipo_liquidacion: str, fecha: date
    ) -> list[TarifaLiquidacionBase]:
        """
        Get ALL TarifaLiquidacionBase records vigente at fecha for a tipo_liquidacion.

        Returns a list (caller decides which to use or validates for overlap).
        Order is DESC by periodo_inicio (newest first).

        Returns:
            List of TarifaLiquidacionBase instances (may be empty).
        """
        qs = (
            TarifaLiquidacionBase.objects
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .vigentes(fecha=fecha)
            .order_by("-periodo_inicio")
        )
        return list(qs)

    # ── TarifaPorcentajeObra ─────────────────────────────────────────────────

    def get_tarifa_porcentaje_obra(
        self, tarifa_base_ids: list[str]
    ) -> list[TarifaPorcentajeObra]:
        """
        Get TarifaPorcentajeObra records for the given TarifaLiquidacionBase IDs.

        Returns:
            List of TarifaPorcentajeObra instances (may be empty).
        """
        if not tarifa_base_ids:
            return []
        return list(
            TarifaPorcentajeObra.objects.filter(
                tarifa_base_id__in=tarifa_base_ids
            ).select_related("tarifa_base").order_by("porcentaje_liquidacion")
        )

    # ── TarifaPorMetroCuadrado ──────────────────────────────────────────────

    def get_tarifa_m2(self, tarifa_base_id: str) -> Optional[TarifaPorMetroCuadrado]:
        """
        Get TarifaPorMetroCuadrado for a single TarifaLiquidacionBase.

        Returns:
            TarifaPorMetroCuadrado instance or None if not found.
        """
        return TarifaPorMetroCuadrado.objects.select_related("tarifa_base").filter(
            tarifa_base_id=tarifa_base_id
        ).first()

    # ── TarifaPorCategoriaVisitas ─────────────────────────────────────────────

    def get_tarifa_categoria_visitas(
        self, tarifa_base_ids: list[str]
    ) -> list[TarifaPorCategoriaVisitas]:
        """
        Get TarifaPorCategoriaVisitas records for the given TarifaLiquidacionBase IDs.

        Returns:
            List of TarifaPorCategoriaVisitas instances (may be empty).
        """
        if not tarifa_base_ids:
            return []
        return list(
            TarifaPorCategoriaVisitas.objects.filter(
                tarifa_base_id__in=tarifa_base_ids
            ).select_related("tarifa_base").order_by("categoria_visitas")
        )

    # ── DerechoPorcentajeObra ───────────────────────────────────────────────

    def get_derecho_porcentaje_vigente(self, fecha: date) -> DerechoPorcentajeObra:
        """
        Get the DerechoPorcentajeObra vigente at the given fecha.

        Uses VigenciaModel.vigentes(fecha=fecha) with DESC ordering.
        NEWEST at fecha = order_by("-periodo_inicio").first()

        Raises:
            NoDerechoVigenteError: If no derecho is vigente at fecha.

        Returns:
            DerechoPorcentajeObra instance vigente at fecha.
        """
        qs = (
            DerechoPorcentajeObra.objects
            .vigentes(fecha=fecha)
            .order_by("-periodo_inicio")
        )
        result = qs.first()
        if result is None:
            raise NoDerechoVigenteError("porcentaje obra", fecha)
        return result

    # ── DerechoPorMetroCuadrado ──────────────────────────────────────────────

    def get_derecho_m2_vigente(self, fecha: date) -> DerechoPorMetroCuadrado:
        """
        Get the DerechoPorMetroCuadrado vigente at the given fecha.

        Uses VigenciaModel.vigentes(fecha=fecha) with DESC ordering.
        NEWEST at fecha = order_by("-periodo_inicio").first()

        Raises:
            NoDerechoVigenteError: If no derecho is vigente at fecha.

        Returns:
            DerechoPorMetroCuadrado instance vigente at fecha.
        """
        qs = (
            DerechoPorMetroCuadrado.objects
            .vigentes(fecha=fecha)
            .order_by("-periodo_inicio")
        )
        result = qs.first()
        if result is None:
            raise NoDerechoVigenteError("por metro cuadrado", fecha)
        return result
