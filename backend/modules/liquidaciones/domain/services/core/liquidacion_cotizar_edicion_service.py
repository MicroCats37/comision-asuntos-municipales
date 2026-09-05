"""
LiquidacionCotizarEdicionService — Read-only quote calculation for edit previews.

Does NOT persist — pure calculation using historical values from
LiquidacionGeneral.fecha_registro.date().

Three engines:
- PO (PorcentajeObra): Edificaciones, Taludes, Impacto Vial
- M2 (PorMetroCuadrado): Habilitación Urbana, Mecánica de Suelos
- Visitas (PorCategoriaVisitas): Inspección de Obra

Design rules:
- Reuses LiquidacionPatchHistoricoCoreService for historical resolution
- Reuses existing calcular_cotizacion_* pure arithmetic
- Does NOT delete/create/update any DB rows
- No transaction.atomic() wrapper (no writes)
- Returns the same result shape as the respective Cotizacion*Result
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado as TarifaPorMetroCuadradoModel,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
    CotizacionPorcentajeObraDetalleResult,
    CotizacionM2Result,
    CotizacionVisitasResult,
    EspecialidadResult,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
    NoIGVVigenteError,
    NoUITVigenteError,
    NoTarifaVigenteError,
    NoDerechoVigenteError,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from core.exceptions import BusinessError


# ── PO (PorcentajeObra) ────────────────────────────────────────────────────────


@dataclass
class CotizarEdicionPOTarifaInput:
    """A single tariff + especialidad pair for PO cotizar-edicion."""
    tarifa_id: str
    especialidad_id: str


@dataclass
class CotizarEdicionPOInput:
    """
    Input for PO (Edificaciones/Taludes/Impacto Vial) cotizar-edicion.

    If a field is None, the current stored value is preserved for calculation.
    """
    valor_declarado: Optional[Decimal] = None
    tarifas: Optional[List[CotizarEdicionPOTarifaInput]] = None


class LiquidacionNoEncontradaError(BusinessError):
    """Raised when LiquidacionGeneral has no type-specific record."""

    def __init__(self, tipo: str, liquidacion_general_id: str):
        super().__init__(
            f"La liquidacion {liquidacion_general_id} no tiene un registro {tipo}. "
            f"No se puede cotizar-edicion."
        )


class LiquidacionCotizarEdicionPOService:
    """
    Read-only quote calculation for PO motor (Edificaciones, Taludes, Impacto Vial).

    Uses historical values (IGV, UIT, tarifas, derecho) by LiquidacionGeneral.fecha_registro.
    Does NOT persist any changes.

    Usage:
        service = LiquidacionCotizarEdicionPOService()
        result = service.cotizar_edicion(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico = LiquidacionPatchHistoricoCoreService()
        self._po_core = LiquidacionPorcentajeObraCoreService()

    def cotizar_edicion(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: CotizarEdicionPOInput,
    ) -> CotizacionPorcentajeObraResult:
        """
        Calculate a quote for editing an existing PO liquidacion.

        Read-only — no DB mutation.

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — valor_declarado and/or tarifas.
                  None values mean "preserve current".

        Returns:
            CotizacionPorcentajeObraResult with the calculated quote.

        Raises:
            LiquidacionNoEncontradaError: No PO record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base at fecha_registro.
            NoDerechoVigenteError: No derecho at fecha_registro.
            BusinessError: If explicit empty tarifas list provided.
        """
        # ── 1. Get PO record ───────────────────────────────────────────────────
        try:
            liq_po = liquidacion_general.liquidacion_porcentaje_obra
        except LiquidacionPorcentajeObra.DoesNotExist:
            raise LiquidacionNoEncontradaError(
                "LiquidacionPorcentajeObra",
                str(liquidacion_general.id),
            )

        # ── 2. Resolve historical financial variables ───────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        igv = self._historico.get_igv_por_fecha(fecha)
        uit = self._historico.get_uit_por_fecha(fecha)
        derecho = self._historico.get_derecho_porcentaje_vigente(fecha)

        # ── 3. Determine valor_declarado ──────────────────────────────────────
        valor_declarado = patch.valor_declarado
        if valor_declarado is None:
            valor_declarado = liq_po.valor_declarado

        # ── 4. Determine tarifas to apply ─────────────────────────────────────
        if patch.tarifas is not None:
            if patch.tarifas:
                tarifas_aplicadas = self._build_tarifa_dtos_from_input(patch.tarifas, fecha)
            else:
                raise BusinessError(
                    "Se requiere al menos una tarifa para cotizar la liquidacion."
                )
        else:
            # Preserve current — rebuild DTOs from existing detail rows
            tarifas_aplicadas = self._build_tarifa_dtos_from_existing_details(liq_po)

        # ── 5. Calculate (pure arithmetic) ────────────────────────────────────
        cotizacion = self._po_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas_aplicadas,
            igv_porcentaje=igv.valor,
            derecho=derecho,
            uit_valor=Decimal(str(uit.valor)),
        )

        # ── 6. Build result (no DB mutation) ──────────────────────────────────
        return CotizacionPorcentajeObraResult(
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado_id=str(derecho.id),
            detalles=[
                CotizacionPorcentajeObraDetalleResult(
                    tarifa_id=d.tarifa_aplicada.tarifa_id,
                    especialidad=EspecialidadResult(
                        id=d.tarifa_aplicada.especialidad_id,
                        nombre=d.tarifa_aplicada.especialidad_nombre or "",
                    ) if d.tarifa_aplicada.especialidad_id else None,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                )
                for d in cotizacion.detalles
            ],
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )

    def _build_tarifa_dtos_from_input(
        self, tarifas: List[CotizarEdicionPOTarifaInput], fecha: date
    ) -> list[TarifaPorcentajeObraAplicada]:
        """
        Build TarifaPorcentajeObraAplicada DTOs from explicit input.

        Validates each tariff was vigente at fecha.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            TarifaPorcentajeObra,
        )

        dtos = []
        vigente_bases = {
            str(base_id)
            for base_id in TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .values_list("id", flat=True)
        }
        for inp in tarifas:
            tarifa_po = TarifaPorcentajeObra.objects.select_related("tarifa_base").get(
                id=inp.tarifa_id
            )
            if str(tarifa_po.tarifa_base_id) not in vigente_bases:
                raise NoTarifaVigenteError(
                    tarifa_po.tarifa_base.tipo_liquidacion.codigo, fecha
                )
            dtos.append(
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(tarifa_po.id),
                    porcentaje_liquidacion=tarifa_po.porcentaje_liquidacion,
                    especialidad_id=inp.especialidad_id,
                    especialidad_nombre=None,
                )
            )
        return dtos

    def _build_tarifa_dtos_from_existing_details(
        self, liq_po: LiquidacionPorcentajeObra
    ) -> list[TarifaPorcentajeObraAplicada]:
        """Rebuild DTOs from existing detail rows (preserve current rates)."""
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


# ── M2 (PorMetroCuadrado) ─────────────────────────────────────────────────────


@dataclass
class CotizarEdicionM2Input:
    """
    Input for M2 (HU/MS) cotizar-edicion.

    If a field is None, the current stored value is preserved for calculation.
    """
    area_solicitada: Optional[Decimal] = None
    tarifa_m2_id: Optional[str] = None


class LiquidacionCotizarEdicionM2Service:
    """
    Read-only quote calculation for M2 motor (Habilitación Urbana, Mecánica de Suelos).

    Uses historical derecho via LiquidacionPatchHistoricoCoreService.
    Does NOT persist any changes.

    Usage:
        service = LiquidacionCotizarEdicionM2Service()
        result = service.cotizar_edicion(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico = LiquidacionPatchHistoricoCoreService()
        self._m2_core = LiquidacionPorMetroCuadradoCoreService()

    def cotizar_edicion(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: CotizarEdicionM2Input,
    ) -> CotizacionM2Result:
        """
        Calculate a quote for editing an existing M2 liquidacion.

        Read-only — no DB mutation.

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — area_solicitada and/or tarifa_m2_id.

        Returns:
            CotizacionM2Result with the calculated quote.

        Raises:
            LiquidacionNoEncontradaError: No M2 record for this liquidacion.
            NoTarifaVigenteError: No tariff base vigente at fecha_registro.
            NoDerechoVigenteError: No derecho at fecha_registro.
        """
        from django.core.exceptions import ObjectDoesNotExist

        # ── 1. Get M2 record ───────────────────────────────────────────────────
        try:
            liq_m2 = liquidacion_general.liquidacion_m2.get()
        except ObjectDoesNotExist:
            raise LiquidacionNoEncontradaError(
                "LiquidacionPorMetroCuadrado",
                str(liquidacion_general.id),
            )

        # ── 2. Resolve historical date ─────────────────────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        # ── 3. Determine area_solicitada ───────────────────────────────────────
        area_solicitada = patch.area_solicitada
        if area_solicitada is None:
            area_solicitada = liq_m2.area_m2

        # ── 4. Resolve tariff ─────────────────────────────────────────────────
        if patch.tarifa_m2_id is not None:
            tarifa_m2 = self._get_tarifa_m2_validated(
                patch.tarifa_m2_id, tipo_liq, fecha
            )
        else:
            tarifa_m2 = liq_m2.tarifa_aplicada

        # ── 5. Resolve historical derecho ──────────────────────────────────────
        derecho = self._historico.get_derecho_m2_vigente(fecha)

        # ── 6. Calculate (pure arithmetic) ────────────────────────────────────
        cotizacion = self._m2_core.calcular_cotizacion_m2(
            tipo_liquidacion=tipo_liq,
            area_solicitada=area_solicitada,
            tarifa_m2_id=str(tarifa_m2.id),
            derecho=derecho,
        )

        # ── 6b. Apply floor/cap (same as M2 orchestrator) ─────────────────────
        if cotizacion.subtotal < cotizacion.minimo:
            cotizacion.subtotal = cotizacion.minimo
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.subtotal > cotizacion.maximo:
            cotizacion.subtotal = cotizacion.maximo
            cotizacion.total = cotizacion.maximo

        return CotizacionM2Result(
            area_m2=area_solicitada,
            costo_por_m2=cotizacion.costo_por_m2,
            tarifa_id=str(tarifa_m2.id),
            derecho_id=str(derecho.id),
            minimo=cotizacion.minimo,
            maximo=cotizacion.maximo,
            monto_bruto=cotizacion.monto_bruto,
            subtotal=cotizacion.subtotal,
            total=cotizacion.total,
        )

    def _get_tarifa_m2_validated(
        self,
        tarifa_m2_id: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorMetroCuadradoModel:
        """Get TarifaPorMetroCuadrado and validate it was vigente at fecha."""
        try:
            tarifa_m2 = TarifaPorMetroCuadradoModel.objects.select_related("tarifa_base").get(
                id=tarifa_m2_id
            )
        except TarifaPorMetroCuadradoModel.DoesNotExist:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        vigente_base_ids = {
            str(base_id)
            for base_id in
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .values_list("id", flat=True)
        }
        if str(tarifa_m2.tarifa_base_id) not in vigente_base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        return tarifa_m2


# ── Visitas (Inspección de Obra) ───────────────────────────────────────────────


@dataclass
class CotizarEdicionVisitasInput:
    """
    Input for Visitas (IO) cotizar-edicion.

    If a field is None, the current stored value is preserved for calculation.
    """
    cantidad_visitas: Optional[int] = None
    categoria: Optional[str] = None
    tarifa_visitas_id: Optional[str] = None


class NoTarifaVisitasError(BusinessError):
    """Raised when no TarifaPorCategoriaVisitas exists for the given categoria and fecha."""

    def __init__(self, categoria: str, fecha: date):
        super().__init__(
            f"No existe tarifa de visitas para la categoria '{categoria}' "
            f"vigente en la fecha {fecha}."
        )


class LiquidacionCotizarEdicionVisitasService:
    """
    Read-only quote calculation for Visitas motor (Inspección de Obra).

    Uses historical IGV, UIT via LiquidacionPatchHistoricoCoreService.
    Does NOT persist any changes.

    Usage:
        service = LiquidacionCotizarEdicionVisitasService()
        result = service.cotizar_edicion(liquidacion_general, patch_input)
    """

    def __init__(self) -> None:
        self._historico = LiquidacionPatchHistoricoCoreService()
        self._visitas_core = LiquidacionPorCategoriaVisitasCoreService()

    def cotizar_edicion(
        self,
        liquidacion_general: LiquidacionGeneral,
        patch: CotizarEdicionVisitasInput,
    ) -> CotizacionVisitasResult:
        """
        Calculate a quote for editing an existing Visitas liquidacion.

        Read-only — no DB mutation.

        Args:
            liquidacion_general: LiquidacionGeneral instance (already fetched).
            patch: Optional patch — cantidad_visitas, categoria, and/or tarifa_visitas_id.

        Returns:
            CotizacionVisitasResult with the calculated quote.

        Raises:
            LiquidacionNoEncontradaError: No Visitas record for this liquidacion.
            NoIGVVigenteError: No IGV at fecha_registro.
            NoUITVigenteError: No UIT at fecha_registro.
            NoTarifaVigenteError: No tariff base vigente at fecha_registro.
            NoTarifaVisitasError: categoria changed but no matching tariff at fecha.
        """
        from django.core.exceptions import ObjectDoesNotExist

        # ── 1. Get Visitas record ──────────────────────────────────────────────
        try:
            liq_visitas = liquidacion_general.liquidacion_visitas.get()
        except ObjectDoesNotExist:
            raise LiquidacionNoEncontradaError(
                "LiquidacionPorCategoriaVisitas",
                str(liquidacion_general.id),
            )

        # ── 2. Resolve historical date and tipo ────────────────────────────────
        fecha = liquidacion_general.fecha_registro.date()
        tipo_liq = liquidacion_general.tipo_liquidacion.codigo

        # ── 3. Resolve historical IGV and UIT ────────────────────────────────
        igv = self._historico.get_igv_por_fecha(fecha)
        uit = self._historico.get_uit_por_fecha(fecha)

        # ── 4. Determine cantidad_visitas ─────────────────────────────────────
        cantidad_visitas = patch.cantidad_visitas
        if cantidad_visitas is None:
            cantidad_visitas = liq_visitas.cantidad_visitas

        # ── 5. Determine tarifa_aplicada ─────────────────────────────────────
        if patch.tarifa_visitas_id is not None:
            tarifa = self._get_tarifa_validated(
                patch.tarifa_visitas_id, tipo_liq, fecha
            )
            categoria = tarifa.categoria_visitas
        elif patch.categoria is not None:
            categoria = patch.categoria
            tarifa = self._get_tarifa_by_categoria(categoria, tipo_liq, fecha)
        else:
            tarifa = liq_visitas.tarifa_aplicada
            categoria = liq_visitas.categoria

        # ── 6. Calculate (pure arithmetic) ───────────────────────────────────
        result = self._visitas_core.calcular_cotizacion_visitas(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_visitas_id=str(tarifa.id),
            uit_vigente=uit,
            igv_vigente=igv,
        )

        if result is None:
            raise NoTarifaVisitasError(categoria, fecha)

        return result

    def _get_tarifa_validated(
        self,
        tarifa_visitas_id: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """Get tariff by ID and validate it was vigente at fecha."""
        try:
            tarifa = TarifaPorCategoriaVisitas.objects.select_related("tarifa_base").get(
                id=tarifa_visitas_id
            )
        except TarifaPorCategoriaVisitas.DoesNotExist:
            raise NoTarifaVisitasError(tarifa_visitas_id, fecha)

        vigente_base_ids = {
            str(base_id)
            for base_id in
            TarifaLiquidacionBase.objects.vigentes(fecha=fecha)
            .filter(tipo_liquidacion__codigo=tipo_liquidacion)
            .values_list("id", flat=True)
        }
        if str(tarifa.tarifa_base_id) not in vigente_base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

        return tarifa

    def _get_tarifa_by_categoria(
        self,
        categoria: str,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorCategoriaVisitas:
        """Get tariff by categoria name and validate it was vigente at fecha."""
        base_ids = [
            tb.id for tb in
            self._historico.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        ]
        if not base_ids:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)

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
