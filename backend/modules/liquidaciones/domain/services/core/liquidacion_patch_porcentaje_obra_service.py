"""
LiquidacionPatchPorcentajeObraService — recalculo PATCH para motor PO (Edificaciones, Taludes, Impacto Vial).

ALCANCE: Solo servicio — sin controller, sin exposición API. El siguiente paquete integra el endpoint.

Aplica a tipos PO: Edificaciones, Impacto Vial, Taludes.

Reglas clave:
- Resuelve IGV/UIT/tarifas/derecho por LiquidacionGeneral.fecha_registro.date()
  vía LiquidacionPatchHistoricoCoreService (NO vigentes actuales).
- Recalcula vía calcular_cotizacion_po existente (aritmética pura, sin lógica de fecha).
- Filas de detalle: eliminar + recrear atómicamente (UniqueConstraint
  (liquidacion_porcentaje, especialidad) impide upsert simple).
- Totales del PO padre + LiquidacionGeneral actualizados en la misma transacción.
- Si se omite un campo del patch, preserva el valor actual/detalles aplicados actuales.
- Lanza BusinessError claro si falta tarifa/derecho/IGV/UIT histórico.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    CotizacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from core.exceptions import BusinessError


class LiquidacionNoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no LiquidacionPorcentajeObra."""

    def __init__(self, liquidacion_general_id):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro "
            f"LiquidacionPorcentajeObra. No se puede recalcular."
        )


@dataclass
class TarifaPatchInput:
    """A single tariff + especialidad pair for PATCH recalculation."""
    tarifa_id: str
    especialidad_id: str


@dataclass
class PatchPorcentajeObraInput:
    """
    Optional patch inputs for PO recalculation.

    If a field is None, the current value is preserved.
    """
    valor_declarado: Optional[Decimal] = None
    tarifas: Optional[list[TarifaPatchInput]] = None
    tipo_tramite: Optional[str] = None


class LiquidacionPatchPorcentajeObraService:
    """
    Recalculation service for PO-type liquidaciones via PATCH.

    Sync core service — caller provides transaction.atomic() if needed.

    Usage:
        service = LiquidacionPatchPorcentajeObraService()
        with transaction.atomic():
            service.recalcular(liquidacion_general_id, patch_input)
    """

    def __init__(self) -> None:
        self._historico_service = LiquidacionPatchHistoricoCoreService()
        self._po_core = LiquidacionPorcentajeObraCoreService()

    def recalcular(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchPorcentajeObraInput,
    ) -> LiquidacionPorcentajeObra:
        """
        Recalculate a PO liquidacion with optional patch inputs.

        All DB writes happen inside this method (caller wraps in transaction.atomic).

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched, with PO lock if needed).
            patch: Optional patch — valor_declarado and/or tarifas.

        Returns:
            Updated LiquidacionPorcentajeObra instance (caller should refresh).

        Raises:
            LiquidacionNoEncontradaError: No PO record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base at fecha_registro.
            NoDerechoVigenteError: No derecho at fecha_registro.
        """
        # ── 1. Get PO record ───────────────────────────────────────────────────
        try:
            liq_po = liquidacion_general.liquidacion_porcentaje_obra
        except LiquidacionPorcentajeObra.DoesNotExist:
            raise LiquidacionNoEncontradaError(str(liquidacion_general.id))

        # ── 2. Resolve historical financial variables ───────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        igv = self._historico_service.get_igv_por_fecha(fecha)
        uit = self._historico_service.get_uit_por_fecha(fecha)
        derecho = self._historico_service.get_derecho_porcentaje_vigente(fecha)

        # ── 3. Determine valor_declarado ──────────────────────────────────────
        valor_declarado = patch.valor_declarado
        if valor_declarado is None:
            valor_declarado = liq_po.valor_declarado

        # ── 4. Determine tarifas to apply ─────────────────────────────────────
        if patch.tarifas is not None:
            # Explicit tariff list provided — build DTOs from input
            if patch.tarifas:
                tarifas_aplicadas = self._build_tarifa_dtos_from_input(patch.tarifas, fecha)
            else:
                # Empty list = no tarifas — must raise since calcular_cotizacion_po requires at least one
                raise BusinessError(
                    "Se requiere al menos una tarifa para recalcular la liquidacion."
                )
        else:
            # None = preserve current — rebuild DTOs from existing detail rows
            tarifas_aplicadas = self._build_tarifa_dtos_from_existing_details(liq_po)

        # ── 5. Recalculate ───────────────────────────────────────────────────
        cotizacion = self._po_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas_aplicadas,
            igv_porcentaje=igv.valor,
            derecho=derecho,
            uit_valor=Decimal(str(uit.valor)),
        )

        # ── 6. Delete + recreate details atomically ───────────────────────────
        # django-simple-history creates HistoricalRecords for deleted rows — expected.
        liq_po.detalles.all().delete()

        for detalle in cotizacion.detalles:
            tarifa = detalle.tarifa_aplicada
            LiquidacionPorcentajeObraDetalle.objects.create(
                liquidacion_porcentaje=liq_po,
                tarifa_aplicada_id=tarifa.tarifa_id,
                especialidad_id=tarifa.especialidad_id,
                porcentaje_aplicado=detalle.porcentaje_aplicado,
                subtotal=detalle.subtotal,
            )

        # ── 7. Update parent PO ───────────────────────────────────────────────
        liq_po.valor_declarado = valor_declarado
        if patch.tipo_tramite is not None:
            liq_po.tipo_tramite = patch.tipo_tramite
        liq_po.porcentaje_liquidacion = cotizacion.porcentaje_liquidacion
        liq_po.derecho_minimo = cotizacion.derecho_minimo
        liq_po.derecho_maximo = cotizacion.derecho_maximo
        liq_po.porcentaje_minimo_uit = cotizacion.porcentaje_minimo_uit
        liq_po.derecho_aplicado = derecho
        liq_po.save()

        # ── 8. Update LiquidacionGeneral totals ───────────────────────────────
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.igv_snapshot = igv.valor
        liquidacion_general.uit_snapshot = Decimal(str(uit.valor))
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit
        liquidacion_general.save()

        return liq_po

    def _build_tarifa_dtos_from_input(
        self, tarifas: list[TarifaPatchInput], fecha: date
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Build TarifaPorcentajeObraAplicada DTOs from explicit patch input.

        Validates that each TarifaPorcentajeObra's TarifaLiquidacionBase is vigente
        at fecha (historical date of the liquidacion). Raises NoTarifaVigenteError
        if a provided tariff is not vigente for the historical date.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            TarifaPorcentajeObra,
            TarifaLiquidacionBase,
        )
        from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
            NoTarifaVigenteError,
        )

        dtos = []
        vigente_bases = set(
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha).values_list("id", flat=True)
        )
        for inp in tarifas:
            tarifa_po = TarifaPorcentajeObra.objects.select_related("tarifa_base").get(
                id=inp.tarifa_id
            )
            if tarifa_po.tarifa_base_id not in vigente_bases:
                raise NoTarifaVigenteError(
                    tarifa_po.tarifa_base.tipo_liquidacion.codigo, fecha
                )
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(tarifa_po.id),
                    porcentaje_liquidacion=tarifa_po.porcentaje_liquidacion,
                    especialidad_id=str(inp.especialidad_id),
                    especialidad_nombre=None,
                )
            )
        return dtos

    def _build_tarifa_dtos_from_existing_details(
        self, liq_po: LiquidacionPorcentajeObra
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Rebuild TarifaPorcentajeObraAplicada DTOs from existing detail rows.

        Preserves the currently applied percentages (detalle.porcentaje_aplicado)
        so recalculation uses the same rates that were originally applied.
        Only the tariff IDs are used to fetch the latest percentage_liquidacion
        from the tariff record (in case it changed), but the detail's stored
        percentage is used in the DTO to ensure the calculation is stable.
        """
        dtos = []
        for detalle in liq_po.detalles.all():
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(detalle.tarifa_aplicada_id),
                    porcentaje_liquidacion=detalle.porcentaje_aplicado,
                    especialidad_id=str(detalle.especialidad_id),
                    especialidad_nombre=None,
                )
            )
        return dtos
