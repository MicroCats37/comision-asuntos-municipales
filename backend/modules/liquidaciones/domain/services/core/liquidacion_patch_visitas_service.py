"""
LiquidacionPatchVisitasService — PATCH recalculation for Visitas motor (Inspección de Obra).

SCOPE: Service only — no controller, no API exposure. Next package integrates endpoint.

Applies to Visitas type: Inspeccion Obra.

Key rules:
- Resolves IGV/UIT by LiquidacionGeneral.fecha_registro.date()
  via LiquidacionPatchHistoricoCoreService (NOT current vigentes).
- Tarifa resolved via TarifaLiquidacionBase vigente at fecha_registro.
- If patch.tarifa_visitas_id is provided: validates it exists and its base
  was vigente at fecha_registro.
- If patch.tarifa_visitas_id is None: preserves currently stored TarifaPorCategoriaVisitas.
- If patch.categoria is provided without patch.tarifa_visitas_id:
  looks up the TarifaPorCategoriaVisitas for that categoria + historical base.
  Raises if no matching tariff found for the historical date.
- Pure arithmetic via existing calcular_cotizacion_visitas (IGV applied to Visitas total).
- Single-row in-place update of LiquidacionPorCategoriaVisitas.
- LiquidacionGeneral.sub_total and .total updated atomically.
- igv_snapshot and uit_snapshot updated (Visitas uses IGV in total).
- Preserves omitted patch fields (cantidad_visitas, categoria, tarifa_visitas_id).
- Raises clear BusinessError if historical IGV/UIT/tariff missing or tariff not found.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
    NoIGVVigenteError,
    NoUITVigenteError,
    NoTarifaVigenteError,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from core.exceptions import BusinessError


class LiquidacionVisitasNoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no LiquidacionPorCategoriaVisitas."""

    def __init__(self, liquidacion_general_id: str):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro "
            f"LiquidacionPorCategoriaVisitas. No se puede recalcular."
        )


class NoTarifaVisitasError(BusinessError):
    """Raised when no TarifaPorCategoriaVisitas exists for the given categoria and fecha."""

    def __init__(self, categoria: str, fecha: date):
        super().__init__(
            f"No existe tarifa de visitas para la categoria '{categoria}' "
            f"vigente en la fecha {fecha}. No se puede recalcular."
        )


@dataclass
class PatchVisitasInput:
    """
    Optional patch inputs for Visitas recalculation.

    If a field is None, the current stored value is preserved.
    """
    cantidad_visitas: Optional[int] = None
    categoria: Optional[str] = None
    tarifa_visitas_id: Optional[str] = None


class LiquidacionPatchVisitasService:
    """
    Recalculation service for Visitas-type liquidaciones (Inspección de Obra) via PATCH.

    Sync core service — caller provides transaction.atomic() if needed.

    Usage:
        service = LiquidacionPatchVisitasService()
        with transaction.atomic():
            service.recalcular(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico_service = LiquidacionPatchHistoricoCoreService()
        self._visitas_core = LiquidacionPorCategoriaVisitasCoreService()

    def recalcular(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: PatchVisitasInput,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Recalculate a Visitas liquidacion with optional patch inputs.

        All DB writes happen inside this method (caller wraps in transaction.atomic).

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — cantidad_visitas, categoria, and/or tarifa_visitas_id.

        Returns:
            Updated LiquidacionPorCategoriaVisitas instance (caller should refresh).

        Raises:
            LiquidacionVisitasNoEncontradaError: No Visitas record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base vigente at fecha_registro
                                  (when explicit tarifa_visitas_id provided but its
                                  base is not vigente at fecha_registro).
            NoTarifaVisitasError: categoria changed but no matching tariff for that
                                  categoria at fecha_registro.
        """
        # ── 1. Get Visitas record via reverse FK accessor ────────────────────────
        # LiquidacionPorCategoriaVisitas has ForeignKey to LiquidacionGeneral with
        # related_name="liquidacion_visitas" — use .get() to fetch the single object.
        try:
            liq_visitas = liquidacion_general.liquidacion_visitas.get()
        except ObjectDoesNotExist:
            raise LiquidacionVisitasNoEncontradaError(str(liquidacion_general.id))

        # ── 2. Resolve historical date and tipo ───────────────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        # ── 3. Resolve historical IGV and UIT ────────────────────────────────────
        igv = self._historico_service.get_igv_por_fecha(fecha)
        uit = self._historico_service.get_uit_por_fecha(fecha)

        # ── 4. Determine cantidad_visitas ───────────────────────────────────────
        cantidad_visitas = patch.cantidad_visitas
        if cantidad_visitas is None:
            cantidad_visitas = liq_visitas.cantidad_visitas

        # ── 5. Determine tarifa_aplicada (most complex rule) ───────────────────
        if patch.tarifa_visitas_id is not None:
            # Explicit tariff ID provided — validate it exists and its base
            # was vigente at fecha_registro (historical accuracy).
            tarifa = self._get_tarifa_validated(patch.tarifa_visitas_id, tipo_liq, fecha)
            # Use the tariff's categoria_visitas as the categoria.
            categoria = tarifa.categoria_visitas
        elif patch.categoria is not None:
            # Only categoria changed — look up the TarifaPorCategoriaVisitas
            # for this categoria + historical base. Raises NoTarifaVisitasError
            # if no matching tariff found for the historical date.
            categoria = patch.categoria
            tarifa = self._get_tarifa_by_categoria(categoria, tipo_liq, fecha)
        else:
            # Neither tariff nor categoria provided — preserve current tariff.
            tarifa = liq_visitas.tarifa_aplicada
            categoria = liq_visitas.categoria

        # ── 6. Recalculate via existing pure arithmetic ─────────────────────────
        cotizacion = self._visitas_core.calcular_cotizacion_visitas(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_visitas_id=str(tarifa.id),
            uit_vigente=uit,
            igv_vigente=igv,
        )
        if cotizacion is None:
            # This should not happen if tariff validation above succeeded,
            # but guard defensively.
            raise NoTarifaVisitasError(categoria, fecha)

        # ── 7. Update Visitas row in-place ──────────────────────────────────────
        liq_visitas.cantidad_visitas = cantidad_visitas
        liq_visitas.categoria = categoria
        liq_visitas.porcentaje_uit = Decimal(str(tarifa.porcentaje_uit))
        liq_visitas.tarifa_aplicada = tarifa
        liq_visitas.save()

        # ── 8. Update LiquidacionGeneral totals ─────────────────────────────────
        liquidacion_general.sub_total = Decimal(str(cotizacion.subtotal))
        liquidacion_general.total = Decimal(str(cotizacion.total))
        liquidacion_general.igv_snapshot = igv.valor
        liquidacion_general.uit_snapshot = Decimal(str(uit.valor))
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit
        liquidacion_general.save()

        return liq_visitas

    def _get_tarifa_validated(
        self,
        tarifa_visitas_id: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """
        Get a TarifaPorCategoriaVisitas by ID and validate it was vigente at fecha.

        Raises:
            NoTarifaVigenteError: if the tariff's TarifaLiquidacionBase is not
                                  vigente at fecha (historical accuracy violation).
            NoTarifaVisitasError: if the tariff ID does not exist.
        """
        try:
            tarifa = TarifaPorCategoriaVisitas.objects.select_related("tarifa_base").get(
                id=tarifa_visitas_id
            )
        except TarifaPorCategoriaVisitas.DoesNotExist:
            raise NoTarifaVisitasError(tarifa_visitas_id, fecha)

        # Validate the tariff's base was vigente at fecha_registro
        # Use TarifaLiquidacionBase.vigentes() (VigenciaModel) not the visitas model.
        vigente_base_ids = set(
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .values_list("id", flat=True)
        )
        if tarifa.tarifa_base_id not in vigente_base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        return tarifa

    def _get_tarifa_by_categoria(
        self,
        categoria: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """
        Get a TarifaPorCategoriaVisitas by categoria name and validate its base
        was vigente at fecha.

        Used when categoria is changed without an explicit tariff ID — we need
        to find the tariff that corresponds to the new categoria for the
        historical date.

        Raises:
            NoTarifaVisitasError: if no tariff exists for this categoria at fecha,
                                  or if the tariff's base was not vigente at fecha.
        """
        # Get all TarifaLiquidacionBase vigente at fecha for this tipo.
        base_ids = [
            tb.id for tb in
            self._historico_service.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        ]
        if not base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        # Find the TarifaPorCategoriaVisitas matching this categoria.
        tarifa = (
            TarifaPorCategoriaVisitas.objects
            .filter(tarifa_base_id__in=base_ids)
            .filter(categoria_visitas=categoria)
            .select_related("tarifa_base")
            .first()
        )
        if tarifa is None:
            raise NoTarifaVisitasError(categoria, fecha)

        return tarifa
