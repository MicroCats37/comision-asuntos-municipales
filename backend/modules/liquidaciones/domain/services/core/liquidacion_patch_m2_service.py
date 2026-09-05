"""
LiquidacionPatchM2Service — PATCH recalculation for M2 motor (Habilitación Urbana, Mecánica de Suelos).

SCOPE: Service only — no controller, no API exposure. Next package integrates endpoint.

Applies to M2 types: Habilitación Urbana, Mecánica de Suelos.

Key rules:
- Resolves derecho via LiquidacionPatchHistoricoCoreService (NOT current vigentes).
- Tarifa resolved via TarifaLiquidacionBase vigente at fecha_registro.
- If patch.tarifa_m2_id is provided: validates it exists and its base was vigente at fecha_registro.
- If patch.tarifa_m2_id is None: uses the currently stored TarifaPorMetroCuadrado.
- Pure arithmetic via existing calcular_cotizacion_m2 (no IGV in M2 total).
- Single-row in-place update of LiquidacionPorMetroCuadrado.
- LiquidacionGeneral.sub_total and .total updated atomically.
- Preserves omitted patch fields (area_solicitada, tarifa_m2_id).
- M2 total = subtotal = monto_bruto (no IGV applied).
- igv_snapshot and uit_snapshot NOT updated (M2 doesn't use them in calculation).
- Raises clear BusinessError if historical derecho missing or tariff not found.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado as TarifaPorMetroCuadradoModel,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
    NoDerechoVigenteError,
    NoTarifaVigenteError,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from core.exceptions import BusinessError


class LiquidacionM2NoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no LiquidacionPorMetroCuadrado."""

    def __init__(self, liquidacion_general_id: str):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro "
            f"LiquidacionPorMetroCuadrado. No se puede recalcular."
        )


@dataclass
class PatchM2Input:
    """
    Optional patch inputs for M2 recalculation.

    If a field is None, the current stored value is preserved.
    """
    area_solicitada: Optional[Decimal] = None
    tarifa_m2_id: Optional[str] = None


class LiquidacionPatchM2Service:
    """
    Recalculation service for M2-type liquidaciones (HU, MS) via PATCH.

    Sync core service — caller provides transaction.atomic() if needed.

    Usage:
        service = LiquidacionPatchM2Service()
        with transaction.atomic():
            service.recalcular(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico_service = LiquidacionPatchHistoricoCoreService()
        self._m2_core = LiquidacionPorMetroCuadradoCoreService()

    def recalcular(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchM2Input,
    ) -> LiquidacionPorMetroCuadrado:
        """
        Recalculate an M2 liquidacion with optional patch inputs.

        All DB writes happen inside this method (caller wraps in transaction.atomic).

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — area_solicitada and/or tarifa_m2_id.

        Returns:
            Updated LiquidacionPorMetroCuadrado instance (caller should refresh).

        Raises:
            LiquidacionM2NoEncontradaError: No M2 record for this liquidacion.
            NoTarifaVigenteError: No tariff base vigente at fecha_registro
                                  (when explicit tarifa_m2_id provided but its base
                                  is not vigente at fecha_registro).
            NoDerechoVigenteError: No derecho vigente at fecha_registro.
        """
        # ── 1. Get M2 record via reverse FK accessor ─────────────────────────────
        # LiquidacionPorMetroCuadrado has ForeignKey to LiquidacionGeneral with
        # related_name="liquidacion_m2" — use .get() to fetch the single object.
        try:
            liq_m2 = liquidacion_general.liquidacion_m2.get()
        except ObjectDoesNotExist:
            raise LiquidacionM2NoEncontradaError(str(liquidacion_general.id))

        # ── 2. Resolve historical date ───────────────────────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        # ── 3. Determine area_solicitada ───────────────────────────────────────
        area_solicitada = patch.area_solicitada
        if area_solicitada is None:
            area_solicitada = liq_m2.area_m2

        # ── 4. Resolve tariff ──────────────────────────────────────────────────
        if patch.tarifa_m2_id is not None:
            # Explicit tariff provided — validate it exists and its base was vigente
            # at fecha_registro (historical accuracy)
            tarifa_m2 = self._get_tarifa_m2_validated(patch.tarifa_m2_id, tipo_liq, fecha)
        else:
            # Preserve current tariff — get the currently stored TarifaPorMetroCuadrado
            tarifa_m2 = liq_m2.tarifa_aplicada

        # ── 5. Resolve historical derecho ──────────────────────────────────────
        derecho = self._historico_service.get_derecho_m2_vigente(fecha)

        # ── 6. Recalculate (pure arithmetic — no IGV in M2) ───────────────────
        # Pass pre-resolved historical derecho so calcular_cotizacion_m2 doesn't
        # call vigentes() which would return the current (wrong) derecho.
        cotizacion = self._m2_core.calcular_cotizacion_m2(
            tipo_liquidacion=tipo_liq,
            area_solicitada=area_solicitada,
            tarifa_m2_id=str(tarifa_m2.id),
            derecho=derecho,
        )

        # ── 6b. Apply floor (orchestrator pattern — cotizacion.subtotal starts as monto_bruto) ─
        if cotizacion.subtotal < cotizacion.minimo:
            cotizacion.subtotal = cotizacion.minimo
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.subtotal > cotizacion.maximo:
            cotizacion.subtotal = cotizacion.maximo
            cotizacion.total = cotizacion.maximo

        # ── 7. Update M2 row in-place ───────────────────────────────────────────
        liq_m2.area_m2 = Decimal(str(area_solicitada))
        liq_m2.costo_por_m2 = Decimal(str(cotizacion.costo_por_m2))
        liq_m2.derecho_minimo = Decimal(str(cotizacion.minimo))
        liq_m2.derecho_maximo = (
            Decimal(str(cotizacion.maximo)) if cotizacion.maximo is not None else None
        )
        liq_m2.tarifa_aplicada = tarifa_m2
        liq_m2.derecho = derecho
        liq_m2.save()

        # ── 8. Update LiquidacionGeneral totals ─────────────────────────────────
        # M2 total = subtotal = monto_bruto (no IGV applied to M2)
        liquidacion_general.sub_total = Decimal(str(cotizacion.subtotal))
        liquidacion_general.total = Decimal(str(cotizacion.total))
        liquidacion_general.save()

        return liq_m2

    def _get_tarifa_m2_validated(
        self,
        tarifa_m2_id: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorMetroCuadradoModel:
        """
        Get a TarifaPorMetroCuadrado by ID and validate it was vigente at fecha.

        Raises:
            NoTarifaVigenteError: if the tariff's TarifaLiquidacionBase is not
                                  vigente at fecha (historical accuracy violation).
        """
        try:
            tarifa_m2 = TarifaPorMetroCuadradoModel.objects.select_related("tarifa_base").get(
                id=tarifa_m2_id
            )
        except TarifaPorMetroCuadradoModel.DoesNotExist:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        # Validate the tariff's base was vigente at fecha_registro
        # Use TarifaLiquidacionBase.vigentes() (VigenciaModel) not the M2 model
        vigente_base_ids = set(
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .values_list("id", flat=True)
        )
        if tarifa_m2.tarifa_base_id not in vigente_base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        return tarifa_m2
