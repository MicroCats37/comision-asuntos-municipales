"""
FinanzasCoreService — ORM queries for finanzas entities.

Pure ORM access. No business logic.
"""
import uuid
from datetime import date
from typing import Optional

from decimal import Decimal
from django.db.models import Prefetch, Q

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.registro_pago_inspector import (
    RegistroPagoInspector,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObraDetalle,
)


def _parse_periodo_year(periodo: str) -> Optional[int]:
    """Extrae el año (int) de un periodo 'YYYY-MM'. None si no parseable."""
    try:
        return int(str(periodo).split("-")[0])
    except (ValueError, TypeError, IndexError):
        return None


def _parse_periodo_mes(periodo: str) -> Optional[int]:
    """Extrae el mes (int, 1-12) de un periodo 'YYYY-MM'. None si no parseable."""
    try:
        return int(str(periodo).split("-")[1])
    except (ValueError, TypeError, IndexError):
        return None


# ── RH Delegado Tipo Liquidación Classification ──────────────────────────────────

PO_TIPO_LIQUIDACION_CODES = frozenset({
    "EDIFICACION",
    "IMPACTO_VIAL",
    "TALUDES",
})

M2_TIPO_LIQUIDACION_CODES = frozenset({
    "HABILITACION_URBANA",
    "MECANICA_SUELOS",
})

# Sentinel values for the strategy returned by get_liquidacion_tipo_estrategia_rh.
TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL = "detail"
TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT = "direct"


def get_liquidacion_tipo_estrategia_rh(
    tipo_liquidacion_codigo: str,
) -> str:
    """
    Clasifica el tipo de liquidación según la estrategia de extracción de base imponible
    usada en el RH del Delegado Operativo.

    Strategy ``detail`` (PO / Porcentaje de Obra):
        La base imponible se extrae de LiquidacionPorcentajeObraDetalle.subtotal
        filtrado por especialidad_revision. Usado para EDIFICACION, IMPACTO_VIAL, TALUDES.

    Strategy ``direct`` (M2 / Por Metro Cuadrado):
        La base imponible es LiquidacionGeneral.sub_total directamente, sin distribución
        por especialidad. Usado para HABILITACION_URBANA, MECANICA_SUELOS.

    Args:
        tipo_liquidacion_codigo: Valor ``codigo`` del TipoLiquidacion, ej. "EDIFICACION",
            "HABILITACION_URBANA".

    Returns:
        TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL o TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT.

    Raises:
        ValueError: Cuando el código de tipo de liquidación no es soportado para RH Delegado.
    """
    if tipo_liquidacion_codigo in PO_TIPO_LIQUIDACION_CODES:
        return TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL
    if tipo_liquidacion_codigo in M2_TIPO_LIQUIDACION_CODES:
        return TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT
    raise ValueError(
        f"Tipo de liquidación '{tipo_liquidacion_codigo}' no soportado en RH Delegado. "
        f"Códigos soportados para estrategia 'detail': {sorted(PO_TIPO_LIQUIDACION_CODES)}. "
        f"Códigos soportados para estrategia 'direct': {sorted(M2_TIPO_LIQUIDACION_CODES)}."
    )


class FinanzasCoreService:
    """
    Core service for querying IGV, UIT, and RH Mensual records.
    """

    def get_igv_vigente(self) -> Optional[IGV]:
        """
        Obtiene el registro de IGV actualmente vigente.

        Returns:
            Instancia de IGV sin periodo_fin, o None si no se encuentra.
        """
        return IGV.objects.vigente()

    def get_uit_vigente(self) -> Optional[UIT]:
        """
        Obtiene el registro de UIT actualmente vigente.

        Returns:
            Instancia de UIT sin periodo_fin, o None si no se encuentra.
        """
        return UIT.objects.vigente()

    # ── Escala de Descuento para Inspectores ───────────────────────────────────

    def get_escala_descuento_vigente(
        self, fecha: date | None = None
    ) -> Optional[EscalaDescuentoInspector]:
        """
        Get the currently active EscalaDescuentoInspector (with its rangos).

        Uses the VigenciaModel.vigentes() manager and returns the most recent.

        Args:
            fecha: Optional date to check against. Defaults to today.

        Returns:
            EscalaDescuentoInspector instance with rangos prefetched, or None.
        """
        if fecha is None:
            fecha = date.today()
        return (
            EscalaDescuentoInspector.objects.vigentes(fecha)
            .prefetch_related("rangos")
            .order_by("-periodo_inicio")
            .first()
        )

    # ── Tasa de Delegado ─────────────────────────────────────────────────────────

    def get_tasa_delegado_vigente(
        self, tipo_liquidacion, fecha: date | None = None
    ) -> Optional[TasaDelegado]:
        """
        Get the currently active TasaDelegado for a given TipoLiquidacion.

        Uses the TasaDelegadoQuerySet.vigentes() manager, filters by the
        tipo_liquidacion, and returns the most recent.

        Args:
            tipo_liquidacion: TipoLiquidacion instance or PK to scope the lookup.
            fecha: Optional date to check against. Defaults to today.

        Returns:
            TasaDelegado instance or None.
        """
        if fecha is None:
            fecha = date.today()
        return (
            TasaDelegado.objects.vigentes(fecha)
            .filter(tipo_liquidacion=tipo_liquidacion)
            .order_by("-periodo_inicio")
            .first()
        )

    def get_rango_para_monto(
        self,
        escala: EscalaDescuentoInspector,
        monto: Decimal,
    ) -> Optional[RangoDescuentoInspector]:
        """
        Get the RangoDescuentoInspector that applies to a given monto.

        Rule: applies when monto_minimo <= monto < monto_maximo, or
        monto >= monto_minimo when monto_maximo is None (sin tope superior).

        Args:
            escala: EscalaDescuentoInspector instance (rangos must be loaded).
            monto: Monto to classify.

        Returns:
            RangoDescuentoInspector or None if no range matches.
        """
        rangos = escala.rangos.all().order_by("monto_minimo")
        for rango in rangos:
            if rango.monto_maximo is None:
                if monto >= rango.monto_minimo:
                    return rango
            elif rango.monto_minimo <= monto < rango.monto_maximo:
                return rango
        return None

    # ── RH Inspector Mensual ───────────────────────────────────────────────────────

    def get_inspector_by_cip(self, cip: str) -> Optional[Inspector]:
        """
        Get an Inspector by CIP from the related perfil_ingeniero.

        Args:
            cip: CIP code from the engineer's profile.

        Returns:
            Inspector instance or None if not found.
        """
        return (
            Inspector.objects
            .select_related("perfil_ingeniero")
            .filter(perfil_ingeniero__cip=cip)
            .first()
        )

    def get_liquidacion_por_expediente(
        self, expediente: str
    ) -> Optional[LiquidacionGeneral]:
        """
        Get a LiquidacionGeneral by expediente.

        Args:
            expediente: Expediente identifier.

        Returns:
            LiquidacionGeneral instance or None if not found.
        """
        return (
            LiquidacionGeneral.objects
            .select_related("tipo_liquidacion")
            .filter(expediente=expediente)
            .first()
        )

    def get_liquidacion_general_by_id(
        self, liquidacion_general_id: int
    ) -> Optional[LiquidacionGeneral]:
        """
        Get a LiquidacionGeneral by primary key.

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.

        Returns:
            LiquidacionGeneral instance or None if not found.
        """
        return (
            LiquidacionGeneral.objects
            .select_related("tipo_liquidacion")
            .filter(id=liquidacion_general_id)
            .first()
        )

    def get_liquidacion_general_with_comprobantes(
        self, liquidacion_general_id: int
    ) -> Optional[LiquidacionGeneral]:
        """
        Get a LiquidacionGeneral with active comprobante prefetched.

        Used by RH Delegado cotizar to avoid N+1 queries when accessing
        comprobante_activo (where activo=True).

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.

        Returns:
            LiquidacionGeneral instance or None if not found.
        """
        active_comprobantes = LiquidacionComprobante.objects.filter(
            activo=True
        ).order_by("-fecha_emision", "-id")
        return (
            LiquidacionGeneral.objects
            .select_related("tipo_liquidacion")
            .filter(id=liquidacion_general_id)
            .prefetch_related(
                Prefetch("comprobantes", queryset=active_comprobantes, to_attr="comprobantes_activos")
            )
            .first()
        )

    def get_liquidacion_categoria_visitas(
        self, liquidacion_general_id: int
    ) -> Optional[LiquidacionPorCategoriaVisitas]:
        """
        Get the LiquidacionPorCategoriaVisitas for a given LiquidacionGeneral.

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.

        Returns:
            LiquidacionPorCategoriaVisitas instance or None if not found.
        """
        return (
            LiquidacionPorCategoriaVisitas.objects
            .filter(liquidacion_general_id=liquidacion_general_id)
            .first()
        )

    def get_liquidacion_categoria_visitas_by_id(
        self, lcv_id: int | str
    ) -> Optional[LiquidacionPorCategoriaVisitas]:
        """
        Get a LiquidacionPorCategoriaVisitas by its primary key (UUID).

        Args:
            lcv_id: PK of the LiquidacionPorCategoriaVisitas (UUID string or int).

        Returns:
            LiquidacionPorCategoriaVisitas instance or None if not found.
        """
        return LiquidacionPorCategoriaVisitas.objects.filter(id=str(lcv_id)).first()

    def get_liquidacion_inspector(
        self,
        liquidacion_categoria_visitas_id: int,
        inspector_id: int,
    ) -> Optional[LiquidacionInspector]:
        """
        Get a LiquidacionInspector for a specific (IO, inspector) pair.

        Args:
            liquidacion_categoria_visitas_id: PK of the LiquidacionPorCategoriaVisitas.
            inspector_id: PK of the Inspector.

        Returns:
            LiquidacionInspector instance or None if not found.
        """
        return (
            LiquidacionInspector.objects
            .filter(
                liquidacion_id=liquidacion_categoria_visitas_id,
                inspector_id=inspector_id,
            )
            .first()
        )

    def get_liquidacion_inspector_by_id(
        self,
        liquidacion_inspector_id: int | str,
    ) -> Optional[LiquidacionInspector]:
        """
        Get a LiquidacionInspector by its primary key.

        Args:
            liquidacion_inspector_id: PK of the LiquidacionInspector.

        Returns:
            LiquidacionInspector instance or None if not found.
        """
        return LiquidacionInspector.objects.filter(id=str(liquidacion_inspector_id)).first()

    def update_liquidacion_inspector_periodo_mes(
        self,
        liquidacion_inspector_id: int | str,
        periodo: int,
        mes: int,
    ) -> None:
        """Update period fields for an existing LiquidacionInspector row."""
        liquidacion_inspector = LiquidacionInspector.objects.get(
            pk=liquidacion_inspector_id,
        )
        liquidacion_inspector.periodo = periodo
        liquidacion_inspector.mes = mes
        liquidacion_inspector.save(update_fields=["periodo", "mes", "updated_at"])

    def get_registro_pago(
        self,
        liquidacion_categoria_visitas_id: int,
        periodo: int,
        mes: int,
    ) -> Optional[RegistroPagoInspector]:
        """
        Get a RegistroPagoInspector for a specific (IO, periodo, mes) tuple.

        Args:
            liquidacion_categoria_visitas_id: PK of the LiquidacionPorCategoriaVisitas.
            periodo: Year of the period (int, e.g. 2026).
            mes: Month of the period (int, 1-12).

        Returns:
            RegistroPagoInspector instance or None if not found.
        """
        return (
            RegistroPagoInspector.objects
            .filter(
                liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
                periodo=periodo,
                mes=mes,
            )
            .first()
        )

    def upsert_registro_pago(
        self,
        liquidacion_categoria_visitas_id: int | str,
        periodo: int,
        mes: int,
        inspecciones_pagadas: int,
    ) -> RegistroPagoInspector:
        """
        Create a RegistroPagoInspector row for one RH payment event.

        Args:
            liquidacion_categoria_visitas_id: PK of the LiquidacionPorCategoriaVisitas.
            periodo: Year of the period (int, e.g. 2026).
            mes: Month of the period (int, 1-12).
            inspecciones_pagadas: Number of inspections paid in this RH.

        Returns:
            Created RegistroPagoInspector instance.
        """
        return RegistroPagoInspector.objects.create(
            liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
            periodo=periodo,
            mes=mes,
            inspecciones_pagadas=inspecciones_pagadas,
            fecha_registro=date.today(),
        )

    def crear_rh_inspector_mensual(
        self,
        inspector_id: int | str,
        periodo: int,
        mes: int,
        escala_id: int | str,
        sub_total: Decimal,
        descuento: Decimal,
        honorarios: Decimal,
        tasa_descuento: Decimal | None = None,
        inspector_operacion_id: int | str | None = None,
    ) -> ReciboHonorarioInspectorMensual:
        """
        Create a new ReciboHonorarioInspectorMensual (always creates, never reuses).

        Args:
            inspector_id: FK to Inspector.
            periodo: Año del periodo (int).
            mes: Mes del periodo (int, 1-12).
            escala_id: FK to EscalaDescuentoInspector.
            sub_total: Subtotal for the month.
            descuento: Discount amount.
            honorarios: Net honorarios to pay.
            tasa_descuento: Frozen discount rate used (e.g. 0.20).
            inspector_operacion_id: Optional FK to InspectorOperacion (derived from selected items).

        Returns:
            Newly created ReciboHonorarioInspectorMensual instance.
        """
        return ReciboHonorarioInspectorMensual.objects.create(
            inspector_id=inspector_id,
            periodo=periodo,
            mes=mes,
            escala_descuento_id=escala_id,
            sub_total=sub_total,
            descuento=descuento,
            honorarios=honorarios,
            tasa_descuento=tasa_descuento,
            inspector_operacion_id=inspector_operacion_id,
        )

    def crear_detalle_honorario(
        self,
        recibo_mensual_id: int | str,
        liquidacion_categoria_visitas_id: int | str,
        inspecciones_liquidadas: int,
        costo_por_inspeccion: Decimal,
        monto_contribuido: Decimal,
        escala_descuento_id: int | str | None = None,
        importe_bruto: Decimal | None = None,
        inspecciones_programadas: int | None = None,
        inspecciones_pagadas_hasta_mes_anterior: int | None = None,
        saldo_restante: Decimal | None = None,
        sub_total: Decimal | None = None,
        descuento: Decimal | None = None,
        honorarios: Decimal | None = None,
        tasa_descuento: Decimal | None = None,
    ) -> DetalleHonorarioInspector:
        """
        Create a DetalleHonorarioInspector record with frozen per-item values.

        All math fields are frozen at creation time so the header can sum them
        without recalculating.

        Args:
            recibo_mensual_id: FK to ReciboHonorarioInspectorMensual.
            liquidacion_categoria_visitas_id: FK to LiquidacionPorCategoriaVisitas.
            inspecciones_liquidadas: Number of inspections liquidated in this detail.
            costo_por_inspeccion: Cost per inspection for this liquidacion.
            monto_contribuido: Monetary contribution from this liquidacion.
            escala_descuento_id: FK to EscalaDescuentoInspector (frozen reference).
            importe_bruto: sub_total from LiquidacionGeneral (frozen reference amount).
            inspecciones_programadas: cantidad_visitas from LiquidacionPorCategoriaVisitas.
            inspecciones_pagadas_hasta_mes_anterior: accumulated historical paid inspections.
            saldo_restante: remaining inspections after this quote.
            sub_total: Frozen item subtotal (equals monto_contribuido).
            descuento: Frozen proportional descuento for this item.
            honorarios: Frozen net honorarios for this item (sub_total - descuento).
            tasa_descuento: Frozen discount rate for this item.

        Returns:
            DetalleHonorarioInspector instance.
        """
        escala_descuento = None
        if escala_descuento_id:
            try:
                escala_descuento = EscalaDescuentoInspector.objects.get(
                    id=escala_descuento_id
                )
            except EscalaDescuentoInspector.DoesNotExist:
                pass

        return DetalleHonorarioInspector.objects.create(
            recibo_mensual_id=recibo_mensual_id,
            liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
            inspecciones_liquidadas=inspecciones_liquidadas,
            costo_por_inspeccion=costo_por_inspeccion,
            monto_contribuido=monto_contribuido,
            escala_descuento=escala_descuento,
            importe_bruto=importe_bruto,
            inspecciones_programadas=inspecciones_programadas,
            inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas_hasta_mes_anterior,
            saldo_restante=saldo_restante,
            sub_total=sub_total,
            descuento=descuento,
            honorarios=honorarios,
            tasa_descuento=tasa_descuento,
        )

    def get_detalles_de_recibo(
        self, recibo_mensual_id: int
    ) -> list[DetalleHonorarioInspector]:
        """
        Get all DetalleHonorarioInspector records for a given ReciboHonorarioInspectorMensual.

        Args:
            recibo_mensual_id: PK of the ReciboHonorarioInspectorMensual.

        Returns:
            List of DetalleHonorarioInspector instances.
        """
        return list(
            DetalleHonorarioInspector.objects.filter(recibo_mensual_id=recibo_mensual_id)
        )

    # ── Inspector Candidatas (RH Mensual) ─────────────────────────────────────────

    def list_liquidaciones_inspector_candidatas(
        self,
        inspector_id: int,
        periodo: int | None = None,
        mes: int | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> list[dict]:
        """
        Get candidatas (LiquidacionInspector with remaining saldo) for an inspector.

        For each LiquidacionInspector assigned to the inspector:
        - Get LiquidacionPorCategoriaVisitas.cantidad_visitas (programadas)
        - Get accumulated RegistroPagoInspector for all periods strictly before
          the requested (periodo, mes) tuple, or all periods if no periodo is supplied
        - Calculate saldo_disponible = programadas - pagadas_acumuladas
        - Return only those with saldo_disponible > 0

        Args:
            inspector_id: PK of the Inspector.
            periodo: Optional year (int, e.g. 2026).
                If provided with mes, accumulates inspections paid in ALL periods
                strictly before this (periodo, mes). If None, accumulates all.
            mes: Optional month (int, 1-12). Requires periodo to be set.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            List of dicts with all fields needed for InspectorCandidataItemResult.
        """
        # Get all LiquidacionInspector records for this inspector
        liquidaciones_inspector = LiquidacionInspector.objects.filter(
            inspector_id=inspector_id
        ).select_related(
            "liquidacion__liquidacion_general",
            "liquidacion__liquidacion_general__proyecto",
            "liquidacion__liquidacion_general__municipalidad",
            "inspector__perfil_ingeniero",
            "especialidad_revision",
        )

        # Apply date range filter on LiquidacionGeneral.fecha_registro
        if fecha_inicio:
            liquidaciones_inspector = liquidaciones_inspector.filter(
                liquidacion__liquidacion_general__fecha_registro__date__gte=fecha_inicio
            )
        if fecha_fin:
            liquidaciones_inspector = liquidaciones_inspector.filter(
                liquidacion__liquidacion_general__fecha_registro__date__lte=fecha_fin
            )

        candidates = []
        for li in liquidaciones_inspector:
            lcv = li.liquidacion
            lg = lcv.liquidacion_general

            # Skip if no liquidacion_general
            if not lg:
                continue

            # Get cantidad_visitas (programadas)
            programadas = lcv.cantidad_visitas or 0
            if programadas <= 0:
                continue

            # Get accumulated inspecciones_pagadas:
            # - If periodo and mes are provided: all RegistroPagoInspector with
            #   (periodo < periodo) OR (periodo == periodo AND mes <= mes)
            #   i.e., includes current period to prevent over-requesting when a
            #   RegistroPagoInspector already exists for this period.
            # - If only periodo (no mes): all RegistroPagoInspector with periodo <= periodo
            # - If no periodo: sum ALL periods (historical total)
            from django.db.models import Q
            registro_qs = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas_id=lcv.id,
            )
            if periodo is not None and mes is not None:
                registro_qs = registro_qs.filter(
                    Q(periodo__lt=periodo) | Q(periodo=periodo, mes__lte=mes)
                )
            elif periodo is not None:
                registro_qs = registro_qs.filter(periodo__lte=periodo)
            pagadas = sum(r.inspecciones_pagadas for r in registro_qs)

            saldo = programadas - pagadas
            # Only include if saldo > 0
            if saldo <= 0:
                continue

            # Calculate costo_por_inspeccion
            sub_total = lg.sub_total or 0
            from decimal import Decimal
            TWO_PLACES = Decimal("0.01")
            costo_por_inspeccion = (
                Decimal(str(sub_total)) / Decimal(programadas)
            ).quantize(TWO_PLACES, rounding="ROUND_HALF_UP")

            perfil = li.inspector.perfil_ingeniero
            # Get nombre_propietario from LiquidacionGeneral.proyecto
            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""
            candidates.append({
                "liquidacion_inspector_id": str(li.id),
                "liquidacion_categoria_visitas_id": str(lcv.id),
                "liquidacion_general_id": str(lg.id),
                "expediente": lg.expediente or "",
                "numero_revision": lg.numero_revision or 1,
                "fecha_registro": (
                    lg.fecha_registro.isoformat() if lg.fecha_registro else ""
                ),
                "inspector_nombre": (
                    perfil.nombre_completo if perfil else ""
                ),
                "inspector_cip": perfil.cip if perfil else "",
                "inspector_dni": perfil.dni if perfil else "",
                "especialidad_nombre": (
                    li.especialidad_revision.nombre
                    if li.especialidad_revision else ""
                ),
                "nombre_propietario": nombre_propietario,
                "cantidad_visitas": programadas,
                "inspecciones_pagadas": pagadas,
                "saldo_disponible": saldo,
                "costo_por_inspeccion": costo_por_inspeccion,
                "total_liquidacion": sub_total,
                "sub_total_liquidacion": sub_total,
            })

        return candidates

    def list_liquidaciones_inspector_candidatas_paginated(
        self,
        inspector_id: int,
        page: int,
        page_size: int,
        expediente: str | None = None,
        numero: int | None = None,
        propietario: str | None = None,
        direccion: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        Get paginated candidatas (LiquidacionInspector with remaining saldo) for an inspector.

        Applies all filters at DB level before counting and slicing.
        Batch-fetches RegistroPagoInspector for the page to avoid N+1.

        Filter semantics:
        - expediente: icontains over LiquidacionGeneral.expediente
        - numero: exact match over LiquidacionPorCategoriaVisitas.numero (IO-specific number)
        - propietario: icontains over LiquidacionGeneral.proyecto.nombre_propietario
        - direccion: icontains over LiquidacionGeneral.proyecto.direccion

        Args:
            inspector_id: PK of the Inspector.
            page: Page number (1-indexed).
            page_size: Elements per page.
            expediente: Optional filter — LiquidacionGeneral.expediente icontains.
            numero: Optional filter — LiquidacionPorCategoriaVisitas.numero exact match.
            propietario: Optional filter — proyecto.nombre_propietario icontains.
            direccion: Optional filter — proyecto.direccion icontains.
            periodo: Optional year (int, e.g. 2026).
            mes: Optional month (int, 1-12). Requires periodo to be set.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            Tuple of (list of dicts for the page, total count before filtering).
        """
        from decimal import Decimal
        from django.db.models import Q, Sum

        qs = LiquidacionInspector.objects.filter(
            inspector_id=inspector_id
        ).select_related(
            "liquidacion__liquidacion_general",
            "liquidacion__liquidacion_general__proyecto",
            "liquidacion__liquidacion_general__municipalidad",
            "inspector__perfil_ingeniero",
            "especialidad_revision",
        )

        # Apply date range filter on LiquidacionGeneral.fecha_registro
        if fecha_inicio:
            qs = qs.filter(
                liquidacion__liquidacion_general__fecha_registro__date__gte=fecha_inicio
            )
        if fecha_fin:
            qs = qs.filter(
                liquidacion__liquidacion_general__fecha_registro__date__lte=fecha_fin
            )

        # Apply expediente filter (LiquidacionGeneral.expediente icontains)
        if expediente:
            qs = qs.filter(liquidacion__liquidacion_general__expediente__icontains=expediente)

        # Apply numero filter (LiquidacionInspeccionObra.numero exact match via
        # liquidacion_general__inspeccion_obra)
        if numero is not None:
            qs = qs.filter(
                liquidacion__liquidacion_general__inspeccion_obra__numero=numero
            )

        # Apply propietario filter (proyecto.nombre_propietario icontains)
        if propietario:
            qs = qs.filter(
                liquidacion__liquidacion_general__proyecto__nombre_propietario__icontains=propietario
            )

        # Apply direccion filter (proyecto.direccion icontains)
        if direccion:
            qs = qs.filter(
                liquidacion__liquidacion_general__proyecto__direccion__icontains=direccion
            )

        # Build the registro filter for saldo computation
        registro_filter = Q()
        if periodo is not None and mes is not None:
            registro_filter = Q(periodo__lt=periodo) | Q(periodo=periodo, mes__lte=mes)
        elif periodo is not None:
            registro_filter = Q(periodo__lte=periodo)

        # Total count before saldo filtering and slicing
        total = qs.count()

        # Slice for pagination
        offset = (page - 1) * page_size
        sliced_qs = qs[offset:offset + page_size]

        # Collect lcv IDs for batch preload of RegistroPagoInspector
        lcv_ids = [li.liquidacion_id for li in sliced_qs]

        # Batch fetch all RegistroPagoInspector for the page's lcv IDs
        registro_map: dict[int, int] = {}
        if lcv_ids:
            registro_qs = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas_id__in=lcv_ids,
            )
            if registro_filter:
                registro_qs = registro_qs.filter(registro_filter)

            # Aggregate pagadas per lcv_id
            agg = registro_qs.values("liquidacion_por_categoria_visitas_id").annotate(
                total_pagadas=Sum("inspecciones_pagadas")
            )
            registro_map = {
                r["liquidacion_por_categoria_visitas_id"]: r["total_pagadas"] or 0
                for r in agg
            }

        # Build candidate dicts for the page
        candidates = []
        for li in sliced_qs:
            lcv = li.liquidacion
            lg = lcv.liquidacion_general

            if not lg:
                continue

            programadas = lcv.cantidad_visitas or 0
            if programadas <= 0:
                continue

            pagadas = registro_map.get(lcv.id, 0)
            saldo = programadas - pagadas
            if saldo <= 0:
                continue

            sub_total = lg.sub_total or 0
            TWO_PLACES = Decimal("0.01")
            costo_por_inspeccion = (
                Decimal(str(sub_total)) / Decimal(programadas)
            ).quantize(TWO_PLACES, rounding="ROUND_HALF_UP")

            perfil = li.inspector.perfil_ingeniero
            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""

            candidates.append({
                "liquidacion_inspector_id": str(li.id),
                "liquidacion_categoria_visitas_id": str(lcv.id),
                "liquidacion_general_id": str(lg.id),
                "expediente": lg.expediente or "",
                "numero_revision": lg.numero_revision or 1,
                "fecha_registro": (
                    lg.fecha_registro.isoformat() if lg.fecha_registro else ""
                ),
                "inspector_nombre": (
                    perfil.nombre_completo if perfil else ""
                ),
                "inspector_cip": perfil.cip if perfil else "",
                "inspector_dni": perfil.dni if perfil else "",
                "especialidad_nombre": (
                    li.especialidad_revision.nombre
                    if li.especialidad_revision else ""
                ),
                "nombre_propietario": nombre_propietario,
                "cantidad_visitas": programadas,
                "inspecciones_pagadas": pagadas,
                "saldo_disponible": saldo,
                "costo_por_inspeccion": costo_por_inspeccion,
                "total_liquidacion": sub_total,
                "sub_total_liquidacion": sub_total,
            })

        return candidates, total

    # ── RH Delegado Mensual ───────────────────────────────────────────────────────

    def get_delegado_by_cip(self, cip: str) -> Optional[Delegado]:
        """
        Get a Delegado by CIP from the related perfil_ingeniero.

        Args:
            cip: CIP code from the engineer's profile.

        Returns:
            Delegado instance or None if not found.
        """
        return (
            Delegado.objects
            .select_related("perfil_ingeniero")
            .filter(perfil_ingeniero__cip=cip)
            .first()
        )

    def get_delegado_operacion_by_id(
        self, operacion_id: uuid.UUID,
    ) -> Optional[DelegadoOperacion]:
        """
        Get a DelegadoOperacion by UUID.

        Args:
            operacion_id: UUID of the DelegadoOperacion.

        Returns:
            DelegadoOperacion instance or None if not found.
        """
        return (
            DelegadoOperacion.objects
            .filter(id=operacion_id)
            .first()
        )

    def get_liquidacion_delegado_por_expediente(
        self,
        liquidacion_general_id: int,
        delegado_id: int,
    ) -> Optional[LiquidacionDelegado]:
        """
        Get a LiquidacionDelegado for a specific (liquidacion_general, delegado) pair.

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.
            delegado_id: PK of the Delegado.

        Returns:
            LiquidacionDelegado instance or None if not found.
        """
        return (
            LiquidacionDelegado.objects
            .filter(
                liquidacion_id=liquidacion_general_id,
                delegado_id=delegado_id,
            )
            .first()
        )

    def get_imp_bruto_delegado(
        self,
        liquidacion_general_id: int,
        especialidad_revision_id: int,
    ) -> Optional[Decimal]:
        """
        Get the imp_bruto from LiquidacionPorcentajeObraDetalle matching
        the given liquidacion_general and especialidad_revision.

        DEPRECATED: Returns only the subtotal for backward compatibility.
        New callers should use get_importes_po_detalle() which returns
        the full breakdown (importe_parcial, ajuste_redondeo, subtotal).

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.
            especialidad_revision_id: PK of the EspecialidadRevision.

        Returns:
            Decimal imp_bruto (subtotal) or None if no matching detail found.
        """
        detalle = (
            LiquidacionPorcentajeObraDetalle.objects
            .filter(
                liquidacion_porcentaje__liquidacion_general_id=liquidacion_general_id,
                especialidad_id=especialidad_revision_id,
            )
            .first()
        )
        if detalle:
            return Decimal(str(detalle.subtotal))
        return None

    def get_importes_po_detalle(
        self,
        liquidacion_general_id: int,
        especialidad_revision_id: int,
    ) -> tuple[Decimal, Decimal, Decimal] | None:
        """
        Get the full importe breakdown from LiquidacionPorcentajeObraDetalle.

        Returns a 3-tuple:
            (importe_parcial, ajuste_redondeo, subtotal)

        Safe fallbacks when fields are NULL:
            - ajuste_redondeo defaults to Decimal("0.00")
            - subtotal defaults to Decimal("0.00")

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.
            especialidad_revision_id: PK of the EspecialidadRevision.

        Returns:
            Tuple (importe_parcial, ajuste_redondeo, subtotal) as Decimals,
            or None if no matching detail found.
        """
        detalle = (
            LiquidacionPorcentajeObraDetalle.objects
            .filter(
                liquidacion_porcentaje__liquidacion_general_id=liquidacion_general_id,
                especialidad_id=especialidad_revision_id,
            )
            .first()
        )
        if not detalle:
            return None

        importe_parcial = Decimal(str(detalle.importe_parcial)) if detalle.importe_parcial is not None else Decimal("0.00")
        ajuste_redondeo = Decimal(str(detalle.ajuste_redondeo)) if detalle.ajuste_redondeo is not None else Decimal("0.00")
        # subtotal is the authoritative amount per specialty (importe_total was redundant with subtotal).
        subtotal_item = Decimal(str(detalle.subtotal))

        return (importe_parcial, ajuste_redondeo, subtotal_item)

    def crear_rh_delegado_mensual(
        self,
        delegado_id: int | str,
        periodo: int,
        mes: int,
        sub_total: Decimal,
        renta_cip: Decimal,
        aporte_codemu: Decimal,
        fondo_comun: Decimal,
        neto_honorario: Decimal,
        delegado_operacion_id: str | None = None,
        tasa_delegado_id: int | str | None = None,
    ) -> ReciboHonorarioDelegadoMensual:
        """
        Create a new ReciboHonorarioDelegadoMensual record.

        Always creates a new record — callers are responsible for ensuring
        no duplicate RH headers are created for the same delegation if that
        is not desired.

        Args:
            delegado_id: FK to Delegado.
            periodo: Año del periodo (int, ej. 2026).
            mes: Mes del periodo (int, 1-12).
            sub_total: Subtotal for the month (sum of frozen detail subtotal values).
            renta_cip: 25% of sub_total + suma_ajustes_redondeo (frozen).
            aporte_codemu: 5% of sub_total (frozen).
            fondo_comun: 10% of sub_total (frozen).
            neto_honorario: Net honorarios to pay (frozen from details).
            delegado_operacion_id: Optional FK to DelegadoOperacion.
            tasa_delegado_id: Optional FK to TasaDelegado (frozen reference).

        Returns:
            Newly created ReciboHonorarioDelegadoMensual instance.
        """
        if delegado_operacion_id:
            # Set required FK fields so the record does not violate NOT NULL constraint.
            # The flujo already validated that the DelegadoOperacion belongs to this delegado,
            # but we look it up here to get the exact Delegado id for the record.
            try:
                delegacion = DelegadoOperacion.objects.get(id=delegado_operacion_id)
                efectivo_delegado_id = delegacion.delegado_id
            except DelegadoOperacion.DoesNotExist:
                # Fall back to passed delegado_id if the lookup fails
                efectivo_delegado_id = (
                    int(delegado_id) if isinstance(delegado_id, str) else delegado_id
                )
            return ReciboHonorarioDelegadoMensual.objects.create(
                delegado_operacion_id=delegado_operacion_id,
                delegado_id=efectivo_delegado_id,
                periodo=periodo,
                mes=mes,
                sub_total=sub_total,
                renta_cip=renta_cip,
                aporte_codemu=aporte_codemu,
                fondo_comun=fondo_comun,
                neto_honorario=neto_honorario,
                tasa_delegado_id=tasa_delegado_id,
            )
        else:
            return ReciboHonorarioDelegadoMensual.objects.create(
                delegado_id=(
                    int(delegado_id) if isinstance(delegado_id, str) else delegado_id
                ),
                periodo=periodo,
                mes=mes,
                sub_total=sub_total,
                renta_cip=renta_cip,
                aporte_codemu=aporte_codemu,
                fondo_comun=fondo_comun,
                neto_honorario=neto_honorario,
                tasa_delegado_id=tasa_delegado_id,
            )

    def crear_liquidacion_delegado(
        self,
        liquidacion_id,
        delegado_id,
        especialidad_revision_id,
        numero_rh: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        dictamen_revision: str | None = None,
        fecha_presentacion=None,
        fecha_revision=None,
        delegado_operacion_id: str | None = None,
    ) -> tuple["LiquidacionDelegado", bool]:
        """
        Create or retrieve a LiquidacionDelegado assignment.

        Used by RHDelegadoMensualCrearFlujo when processing candidatas —
        creates the assignment that did not exist before.
        Uses get-or-create-then-update to support re-cálculo (re-running crear)
        AND to backfill delegado_operacion_id on existing records that lack it.

        Args:
            liquidacion_id: FK to LiquidacionGeneral.
            delegado_id: FK to Delegado.
            especialidad_revision_id: FK to EspecialidadRevision.
            numero_rh: Optional número de orden/RH.
            periodo: Optional año (PositiveSmallInteger).
            mes: Optional mes (1-12).
            dictamen_revision: Optional dictamen.
            fecha_presentacion: Optional date.
            fecha_revision: Optional date.
            delegado_operacion_id: Optional FK to DelegadoOperacion — backfilled
                on existing records that don't yet have it set.

        Returns:
            Tuple of (LiquidacionDelegado, created: bool).
        """
        defaults = {
            "numero_rh": numero_rh,
            "periodo": periodo,
            "mes": mes,
            "dictamen_revision": dictamen_revision,
            "fecha_presentacion": fecha_presentacion,
            "fecha_revision": fecha_revision,
        }
        created = False
        # Try to get existing record first
        existing = LiquidacionDelegado.objects.filter(
            liquidacion_id=liquidacion_id,
            delegado_id=delegado_id,
            especialidad_revision_id=especialidad_revision_id,
        ).first()

        if existing is None:
            # Create new with all fields including delegado_operacion_id
            if delegado_operacion_id:
                defaults["delegado_operacion_id"] = delegado_operacion_id
            obj = LiquidacionDelegado.objects.create(
                liquidacion_id=liquidacion_id,
                delegado_id=delegado_id,
                especialidad_revision_id=especialidad_revision_id,
                **defaults,
            )
            created = True
        else:
            # Existing record found — update non-key fields and backfill
            # delegado_operacion_id if provided and missing
            obj = existing
            for field, value in defaults.items():
                setattr(obj, field, value)
            if delegado_operacion_id and obj.delegado_operacion_id is None:
                obj.delegado_operacion_id = delegado_operacion_id
            obj.save(update_fields=list(defaults.keys()) + (
                ["delegado_operacion_id"] if delegado_operacion_id and obj.delegado_operacion_id is not None else []
            ))

        return obj, created

    def get_liquidacion_delegado_por_ids(
        self,
        liquidacion_general_id: int,
        delegado_id: int,
        especialidad_revision_id: int,
    ) -> Optional[LiquidacionDelegado]:
        """
        Get a LiquidacionDelegado by (liquidacion_general, delegado, especialidad).

        Used after creation to retrieve the newly minted LiquidacionDelegado.id
        for building DetalleHonorarioDelegado.

        Args:
            liquidacion_general_id: PK of the LiquidacionGeneral.
            delegado_id: PK of the Delegado.
            especialidad_revision_id: PK of the EspecialidadRevision.

        Returns:
            LiquidacionDelegado instance or None.
        """
        return (
            LiquidacionDelegado.objects
            .filter(
                liquidacion_id=liquidacion_general_id,
                delegado_id=delegado_id,
                especialidad_revision_id=especialidad_revision_id,
            )
            .first()
        )

    def crear_detalle_honorario_delegado(
        self,
        recibo_mensual_id: int | str,
        liquidacion_delegado_id: int | str,
        imp_bruto: Decimal,
        sub_total: Decimal | None = None,
        renta_cip: Decimal | None = None,
        aporte_codemu: Decimal | None = None,
        fondo_comun: Decimal | None = None,
        neto_honorario: Decimal | None = None,
        tasa_delegado_id: int | str | None = None,
    ) -> DetalleHonorarioDelegado:
        """
        Create a DetalleHonorarioDelegado record with frozen per-item values.

        All tax fields and the tasa_delegado FK are frozen at creation time
        so the header can sum them without recalculating.

        Args:
            recibo_mensual_id: FK to ReciboHonorarioDelegadoMensual.
            liquidacion_delegado_id: FK to LiquidacionDelegado.
            imp_bruto: Importe bruto (subtotal from LiquidacionPorcentajeObraDetalle).
            sub_total: Frozen subtotal for this detail.
            renta_cip: Frozen renta_cip for this detail.
            aporte_codemu: Frozen aporte_codemu for this detail.
            fondo_comun: Frozen fondo_comun for this detail.
            neto_honorario: Frozen neto_honorario for this detail.
            tasa_delegado_id: Optional FK to TasaDelegado (frozen reference).

        Returns:
            DetalleHonorarioDelegado instance.
        """
        return DetalleHonorarioDelegado.objects.create(
            recibo_mensual_id=recibo_mensual_id,
            liquidacion_delegado_id=liquidacion_delegado_id,
            imp_bruto=imp_bruto,
            sub_total=sub_total,
            renta_cip=renta_cip,
            aporte_codemu=aporte_codemu,
            fondo_comun=fondo_comun,
            neto_honorario=neto_honorario,
            tasa_delegado_id=tasa_delegado_id,
        )

    def delete_detalles_honorario_delegado(
        self,
        recibo_mensual_id: int,
    ) -> int:
        """
        Delete all DetalleHonorarioDelegado records for a given ReciboHonorarioDelegadoMensual.

        Args:
            recibo_mensual_id: PK of the ReciboHonorarioDelegadoMensual.

        Returns:
            Number of records deleted.
        """
        count, _ = DetalleHonorarioDelegado.objects.filter(
            recibo_mensual_id=recibo_mensual_id
        ).delete()
        return count

    def list_rh_mensuales_delegados_paginated(
        self,
        page: int,
        page_size: int,
        delegado_cip: str | None = None,
        municipalidad_id: uuid.UUID | None = None,
        periodo: int | None = None,
        mes: int | None = None,
    ) -> tuple[list[ReciboHonorarioDelegadoMensual], int]:
        """
        List ReciboHonorarioDelegadoMensual records with pagination and optional filter.

        Prefetches detalles + liquidacion_delegado + liquidacion to avoid N+1.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            delegado_cip: Filter by CIP (delegado__perfil_ingeniero__cip).
            municipalidad_id: Filter by delegado_operacion.municipalidad_id.
            periodo: Filter by año (from ReciboHonorarioDelegadoMensual.periodo).
            mes: Filter by mes (from ReciboHonorarioDelegadoMensual.mes).

        Returns:
            Tuple of (list of ReciboHonorarioDelegadoMensual, total count).
        """
        qs = (
            ReciboHonorarioDelegadoMensual.objects
            .select_related(
                "delegado__perfil_ingeniero",
                "delegado_operacion__municipalidad",
                "delegado_operacion__tipo_liquidacion",
                "delegado_operacion__especialidad_revision",
            )
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioDelegado.objects.select_related(
                        "liquidacion_delegado__liquidacion",
                        "liquidacion_delegado__delegado_operacion",
                    ).filter(recibo_mensual__isnull=False),
                ),
            )
            .order_by("-periodo")
        )

        if delegado_cip is not None:
            qs = qs.filter(delegado__perfil_ingeniero__cip=delegado_cip)
        if municipalidad_id is not None:
            qs = qs.filter(delegado_operacion__municipalidad_id=municipalidad_id)
        if periodo is not None:
            qs = qs.filter(periodo=periodo)
        if mes is not None:
            qs = qs.filter(mes=mes)

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total

    def list_rh_mensuales_inspectores_paginated(
        self,
        page: int,
        page_size: int,
        inspector_id: int | None = None,
    ) -> tuple[list[ReciboHonorarioInspectorMensual], int]:
        """
        List ReciboHonorarioInspectorMensual records with pagination and optional filter.

        Prefetches detalles + liquidacion_por_categoria_visitas + liquidacion_general to avoid N+1.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            inspector_id: Filter by inspector_id.

        Returns:
            Tuple of (list of ReciboHonorarioInspectorMensual, total count).
        """
        qs = (
            ReciboHonorarioInspectorMensual.objects
            .select_related("inspector__perfil_ingeniero", "escala_descuento")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioInspector.objects.select_related(
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito",
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito__provincia",
                        "liquidacion_por_categoria_visitas__liquidacion_general__inspeccion_obra",
                    ).filter(recibo_mensual__isnull=False),
                ),
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
            )
            .order_by("-periodo")
        )

        if inspector_id is not None:
            qs = qs.filter(inspector_id=inspector_id)

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total

    # ── RH Delegado Mensual — Detail by ID ────────────────────────────────────────

    def get_rh_delegado_mensual_by_id(
        self, recibo_id: uuid.UUID
    ) -> Optional[ReciboHonorarioDelegadoMensual]:
        """
        Get a single ReciboHonorarioDelegadoMensual by UUID with full prefetch.

        Args:
            recibo_id: UUID of the monthly receipt.

        Returns:
            ReciboHonorarioDelegadoMensual instance or None if not found.
        """
        return (
            ReciboHonorarioDelegadoMensual.objects
            .select_related(
                "delegado__perfil_ingeniero",
                "delegado_operacion__municipalidad",
                "delegado_operacion__tipo_liquidacion",
                "delegado_operacion__especialidad_revision",
            )
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioDelegado.objects.select_related(
                        "liquidacion_delegado__liquidacion",
                        "liquidacion_delegado__delegado_operacion",
                    ).filter(recibo_mensual__isnull=False),
                ),
            )
            .filter(id=recibo_id)
            .first()
        )

    def get_rh_delegado_mensual_by_keys(
        self,
        delegado_id: int,
        periodo: int,
        mes: int,
    ) -> Optional[ReciboHonorarioDelegadoMensual]:
        """
        Get a single ReciboHonorarioDelegadoMensual by (delegado_id, periodo, mes).

        Returns None if no receipt exists for that combination.

        Args:
            delegado_id: ID of the delegado.
            periodo: Year (e.g. 2026).
            mes: Month (1-12).

        Returns:
            ReciboHonorarioDelegadoMensual instance or None.
        """
        return (
            ReciboHonorarioDelegadoMensual.objects
            .select_related(
                "delegado__perfil_ingeniero",
                "delegado_operacion__municipalidad",
                "delegado_operacion__tipo_liquidacion",
                "delegado_operacion__especialidad_revision",
            )
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioDelegado.objects.select_related(
                        "liquidacion_delegado__liquidacion",
                        "liquidacion_delegado__delegado_operacion",
                    ).filter(recibo_mensual__isnull=False),
                ),
            )
            .filter(delegado_id=delegado_id, periodo=periodo, mes=mes)
            .first()
        )

    # ── RH Inspector Mensual — Detail by ID ──────────────────────────────────────

    def get_rh_inspector_mensual_by_id(
        self, recibo_id: uuid.UUID
    ) -> Optional[ReciboHonorarioInspectorMensual]:
        """
        Get a single ReciboHonorarioInspectorMensual by UUID with full prefetch.

        Args:
            recibo_id: UUID of the monthly receipt.

        Returns:
            ReciboHonorarioInspectorMensual instance or None if not found.
        """
        return (
            ReciboHonorarioInspectorMensual.objects
            .select_related("inspector__perfil_ingeniero", "escala_descuento")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioInspector.objects.select_related(
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito",
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito__provincia",
                        "liquidacion_por_categoria_visitas__liquidacion_general__inspeccion_obra",
                    ).filter(recibo_mensual__isnull=False),
                ),
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
            )
            .filter(id=recibo_id)
            .first()
        )

    def get_rh_inspector_mensual_by_keys(
        self,
        inspector_id: int,
        periodo: int,
        mes: int,
    ) -> Optional[ReciboHonorarioInspectorMensual]:
        """
        Get a single ReciboHonorarioInspectorMensual by (inspector_id, periodo, mes).

        Returns None if no receipt exists for that combination.

        Args:
            inspector_id: ID of the inspector.
            periodo: Year (e.g. 2026).
            mes: Month (1-12).

        Returns:
            ReciboHonorarioInspectorMensual instance or None.
        """
        return (
            ReciboHonorarioInspectorMensual.objects
            .select_related("inspector__perfil_ingeniero", "escala_descuento")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleHonorarioInspector.objects.select_related(
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito",
                        "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito__provincia",
                        "liquidacion_por_categoria_visitas__liquidacion_general__inspeccion_obra",
                    ).filter(recibo_mensual__isnull=False),
                ),
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
            )
            .filter(inspector_id=inspector_id, periodo=periodo, mes=mes)
            .first()
        )

    # ── RH Detalle List (flat detail rows, NOT monthly grouped) ────────────────

    def list_detalle_honorario_delegado_paginated(
        self,
        page: int,
        page_size: int,
        delegado_id: uuid.UUID | None = None,
        delegado_cip: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        municipalidad_id: uuid.UUID | None = None,
        tipo_liquidacion_codigo: str | None = None,
        numero_liquidacion: int | None = None,
    ) -> tuple[list["DetalleHonorarioDelegado"], int]:
        """
        List DetalleHonorarioDelegado rows directly (flat, ungrouped).

        Queries the detail table directly with optional filters.
        Prefetches: liquidacion_delegado (delegado, liquidacion, especialidad_revision, delegado_operacion).

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            delegado_id: Filter by delegado_id (from liquidacion_delegado.delegado).
            delegado_cip: Filter by CIP (from liquidacion_delegado.delegado.perfil_ingeniero.cip).
                Takes precedence if both delegado_id and delegado_cip are set.
            periodo: Filter by periodo (from liquidacion_delegado). Optional.
            mes: Filter by mes (from liquidacion_delegado).
            municipalidad_id: Filter by liquidacion_delegado.liquidacion.municipalidad_id (from the Liquidacion).
            tipo_liquidacion_codigo: Filter by liquidacion_delegado.liquidacion.tipo_liquidacion.codigo (from the Liquidacion). REQUIRED.
            numero_liquidacion: Filter by the type-specific numero field. Requires tipo_liquidacion_codigo to resolve the correct relation path.

        Returns:
            Tuple of (list of DetalleHonorarioDelegado, total count).
        """
        # Stable, cheap ordering: period first, then detail creation time.
        # Avoid ordering by type-specific liquidacion numero because it adds heavy joins on large lists.
        NUMERO_PATH_MAP = {
            "EDIFICACION": "liquidacion_delegado__liquidacion__edificaciones__numero",
            "HABILITACION_URBANA": "liquidacion_delegado__liquidacion__habilitacion_urbana__numero",
            "INSPECCION_OBRA": "liquidacion_delegado__liquidacion__inspeccion_obra__numero",
            "MECANICA_SUELOS": "liquidacion_delegado__liquidacion__mecanica_suelos__numero",
            "IMPACTO_VIAL": "liquidacion_delegado__liquidacion__impacto_vial__numero",
            "TALUDES": "liquidacion_delegado__liquidacion__taludes__numero",
        }
        order_fields = [
            "-liquidacion_delegado__periodo",
            "-liquidacion_delegado__mes",
            "-created_at",
            "id",
        ]
        qs = (
            DetalleHonorarioDelegado.objects
            .select_related(
                "liquidacion_delegado__delegado__perfil_ingeniero",
                "liquidacion_delegado__liquidacion",
                "liquidacion_delegado__especialidad_revision",
                "liquidacion_delegado__liquidacion__municipalidad",
                "liquidacion_delegado__liquidacion__tipo_liquidacion",
            )
            .order_by(*order_fields)
        )

        if delegado_cip:
            qs = qs.filter(liquidacion_delegado__delegado__perfil_ingeniero__cip=delegado_cip)
        elif delegado_id is not None:
            qs = qs.filter(liquidacion_delegado__delegado_id=delegado_id)
        if periodo is not None:
            qs = qs.filter(liquidacion_delegado__periodo=periodo)
        if mes is not None:
            qs = qs.filter(liquidacion_delegado__mes=mes)
        if municipalidad_id is not None:
            qs = qs.filter(liquidacion_delegado__liquidacion__municipalidad_id=municipalidad_id)
        if tipo_liquidacion_codigo is not None:
            qs = qs.filter(liquidacion_delegado__liquidacion__tipo_liquidacion__codigo=tipo_liquidacion_codigo)

        # Apply numero_liquidacion filter using type-specific path.
        # Requires tipo_liquidacion_codigo to resolve the correct relation.
        if numero_liquidacion is not None and tipo_liquidacion_codigo is not None:
            numero_path = NUMERO_PATH_MAP.get(tipo_liquidacion_codigo)
            if numero_path:
                qs = qs.filter(**{numero_path: numero_liquidacion})

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total

    def list_detalle_honorario_inspector_paginated(
        self,
        page: int,
        page_size: int,
        inspector_id: uuid.UUID | None = None,
        inspector_cip: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        municipalidad_id: uuid.UUID | None = None,
        numero_liquidacion: int | None = None,
    ) -> tuple[list["DetalleHonorarioInspector"], int]:
        """
        List DetalleHonorarioInspector rows directly (flat, ungrouped).

        Queries the detail table directly with optional filters.
        Prefetches: liquidacion_por_categoria_visitas (liquidacion_general, liquidacion_general__proyecto).

        The inspector FK is on the parent ReciboHonorarioInspectorMensual, not directly
        on DetalleHonorarioInspector. We filter via the parent receipt.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            inspector_id: Filter by inspector_id (from parent ReciboHonorarioInspectorMensual).
            inspector_cip: Filter by CIP (from recibo_mensual__inspector__perfil_ingeniero__cip).
                Takes precedence if both inspector_id and inspector_cip are set.
            periodo: Filter by periodo (from parent ReciboHonorarioInspectorMensual).
            mes: Filter by mes (from parent ReciboHonorarioInspectorMensual).
            municipalidad_id: Filter by liquidacion_por_categoria_visitas.liquidacion_general.municipalidad_id.
            numero_liquidacion: Filter by liquidacion_por_categoria_visitas.liquidacion_general.inspeccion_obra.numero.

        Returns:
            Tuple of (list of DetalleHonorarioInspector, total count).
        """
        # Stable, cheap ordering: receipt period first, then detail creation time.
        # Avoid ordering by IO numero because it adds a heavy join on large lists.
        qs = (
            DetalleHonorarioInspector.objects
            .select_related(
                "liquidacion_por_categoria_visitas__liquidacion_general__proyecto",
                "recibo_mensual__inspector__perfil_ingeniero",
                "liquidacion_por_categoria_visitas__liquidacion_general__municipalidad",
                "liquidacion_por_categoria_visitas__liquidacion_general__tipo_liquidacion",
            )
            .prefetch_related(
                "liquidacion_por_categoria_visitas__inspectores__inspector__perfil_ingeniero",
            )
            .order_by(
                "-recibo_mensual__periodo",
                "-recibo_mensual__mes",
                "-created_at",
                "id",
            )
        )

        if inspector_cip:
            qs = qs.filter(
                Q(recibo_mensual__inspector__perfil_ingeniero__cip=inspector_cip)
                | Q(liquidacion_por_categoria_visitas__inspectores__inspector__perfil_ingeniero__cip=inspector_cip)
            ).distinct()
        elif inspector_id is not None:
            qs = qs.filter(
                Q(recibo_mensual__inspector_id=inspector_id)
                | Q(liquidacion_por_categoria_visitas__inspectores__inspector_id=inspector_id)
            ).distinct()
        if periodo is not None:
            qs = qs.filter(
                Q(recibo_mensual__periodo=periodo)
                | Q(liquidacion_por_categoria_visitas__inspectores__periodo=periodo)
            ).distinct()
        if mes is not None:
            qs = qs.filter(
                Q(recibo_mensual__mes=mes)
                | Q(liquidacion_por_categoria_visitas__inspectores__mes=mes)
            ).distinct()
        if municipalidad_id is not None:
            qs = qs.filter(liquidacion_por_categoria_visitas__liquidacion_general__municipalidad_id=municipalidad_id)
        if numero_liquidacion is not None:
            qs = qs.filter(
                liquidacion_por_categoria_visitas__liquidacion_general__inspeccion_obra__numero=numero_liquidacion
            )

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total
