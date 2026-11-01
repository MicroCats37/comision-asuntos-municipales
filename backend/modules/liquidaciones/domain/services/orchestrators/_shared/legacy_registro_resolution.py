"""
Shared historical resolution helpers for the typed legacy registration routes.

These helpers live in the ORCHESTRATOR layer (they raise domain/business
errors and decide the effective date), but they are shared by the six type
orchestrators so the historical resolution logic exists only ONCE.

The resolution itself is delegated to the canonical resolver
(`LiquidacionHistoricoCoreService`): there is NO parallel historical read
path and NO silent fallback to the values currently in force. When a required
historical value does not cover the reference date, the canonical resolver
raises its domain error and the request fails.
"""
from datetime import date
from typing import List

from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
)


class LegacyRegistroResolutionMixin:
    """
    Mixin with the historical resolution used by the six type orchestrators.

    Usage: class MyOrchestrator(LegacyRegistroResolutionMixin, LiquidacionPOValidationMixin):
        ...

    The orchestrator MUST expose `historico_core` (the canonical resolver),
    normally injected via `@inject` on `__init__`.
    """

    historico_core: LiquidacionHistoricoCoreService

    # ── Variables financieras ────────────────────────────────────────────────

    def _resolver_igv_uit_historicos(self, fecha: date):
        """
        Resolve the IGV and UIT effective at `fecha`.

        Returns:
            tuple: (IGV, UIT) ORM instances.

        Raises:
            NoIGVVigenteError / NoUITVigenteError: domain errors raised by the
                canonical resolver when the date is not covered. The request
                never falls back to the current values.
        """
        igv = self.historico_core.get_igv_por_fecha(fecha)
        uit = self.historico_core.get_uit_por_fecha(fecha)
        return igv, uit

    # ── Derechos ─────────────────────────────────────────────────────────────

    def _resolver_derecho_porcentaje_historico(self, fecha: date):
        """Resolve the DerechoPorcentajeObra effective at `fecha`."""
        return self.historico_core.get_derecho_porcentaje_vigente(fecha)

    def _resolver_derecho_m2_historico(self, fecha: date):
        """Resolve the DerechoPorMetroCuadrado effective at `fecha`."""
        return self.historico_core.get_derecho_m2_vigente(fecha)

    # ── Tarifas ──────────────────────────────────────────────────────────────

    def _resolver_tarifa_m2_historica(self, tipo_liquidacion: str, fecha: date):
        """
        Resolve the TarifaPorMetroCuadrado effective at `fecha`.

        Resolution path: TarifaLiquidacionBase vigente at `fecha` → child
        TarifaPorMetroCuadrado.

        Raises:
            NoTarifaVigenteError: domain error when no base tariff covers the date.
            HttpError(400): when the base tariff exists but has no M2 child.
        """
        base = self.historico_core.get_tarifa_base_vigente(tipo_liquidacion, fecha)
        tarifa = self.historico_core.get_tarifa_m2(str(base.id))
        if tarifa is None:
            raise HttpError(
                400,
                f"No hay tarifa por metro cuadrado vigente para {tipo_liquidacion} "
                f"en la fecha indicada.",
            )
        return tarifa

    def _resolver_tarifas_visitas_historicas(
        self, tipo_liquidacion: str, fecha: date
    ) -> List:
        """
        Resolve the TarifaPorCategoriaVisitas effective at `fecha`.

        Raises:
            HttpError(400): when no visitas tariff covers the date.
        """
        bases = self.historico_core.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        if not bases:
            raise HttpError(
                400,
                f"No hay tarifa vigente para {tipo_liquidacion} en la fecha indicada.",
            )
        tarifas = self.historico_core.get_tarifa_categoria_visitas(
            [str(base.id) for base in bases]
        )
        if not tarifas:
            raise HttpError(
                400,
                f"No hay tarifa vigente para {tipo_liquidacion} en la fecha indicada.",
            )
        return tarifas
