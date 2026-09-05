"""
FinanzasCoreService — ORM queries for finanzas entities.

Pure ORM access. No business logic.
"""
import uuid
from datetime import date
from typing import Optional

from decimal import Decimal
from django.db.models import Prefetch

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.models.recibo_honorario_inspector import (
    ReciboHonorarioInspector,
)
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


class FinanzasCoreService:
    """
    Core service for querying IGV, UIT, ReciboHonorarioDelegado, and
    ReciboHonorarioInspector records.
    """

    def get_igv_vigente(self) -> Optional[IGV]:
        """
        Get the currently active IGV record.

        Returns:
            IGV instance with no periodo_fin, or None if not found.
        """
        return IGV.objects.vigente()

    def get_uit_vigente(self) -> Optional[UIT]:
        """
        Get the currently active UIT record.

        Returns:
            UIT instance with no periodo_fin, or None if not found.
        """
        return UIT.objects.vigente()

    def get_recibo_por_liquidacion_delegado(
        self, liquidacion_delegado_id: int
    ) -> Optional[ReciboHonorarioDelegado]:
        """
        Get an existing ReciboHonorarioDelegado by its liquidacion_delegado FK.

        Args:
            liquidacion_delegado_id: PK of the LiquidacionDelegado assignment.

        Returns:
            ReciboHonorarioDelegado instance or None if not found.
        """
        return ReciboHonorarioDelegado.objects.filter(
            liquidacion_delegado_id=liquidacion_delegado_id
        ).first()

    def get_recibo_by_id(
        self, recibo_id: int
    ) -> Optional[ReciboHonorarioDelegado]:
        """
        Get a ReciboHonorarioDelegado by PK with related records loaded.

        Uses select_related to avoid N+1 when building the enriched result.

        Args:
            recibo_id: PK of the ReciboHonorarioDelegado.

        Returns:
            ReciboHonorarioDelegado instance or None if not found.
        """
        return (
            ReciboHonorarioDelegado.objects.select_related(
                "liquidacion_delegado",
                "liquidacion_delegado__delegado",
                "liquidacion_delegado__delegado__perfil_ingeniero",
                "liquidacion_delegado__especialidad_revision",
                "liquidacion_delegado__liquidacion",
                "liquidacion_delegado__liquidacion__proyecto",
                "liquidacion_delegado__liquidacion__municipalidad",
                "liquidacion_delegado__liquidacion__tipo_liquidacion",
            )
            .filter(id=recibo_id)
            .first()
        )

    def crear_recibo(
        self,
        liquidacion_delegado_id: int,
        sub_total: Decimal,
        imp_bruto: Decimal,
        renta_cip: Decimal,
        aporte_codemu: Decimal,
        fondo_comun: Decimal,
        neto_honorario: Decimal,
        honorario: Decimal,
    ) -> tuple[ReciboHonorarioDelegado, bool]:
        """
        Create or retrieve a ReciboHonorarioDelegado.

        Uses get_or_create on liquidacion_delegado to keep the OneToOne idempotent.

        Args:
            liquidacion_delegado_id: FK to LiquidacionDelegado.
            sub_total: Snapshot of LiquidacionGeneral.sub_total.
            imp_bruto: Importe bruto from LiquidacionPorcentajeObraDetalle.
            renta_cip: imp_bruto × 0.25.
            aporte_codemu: imp_bruto × 0.05.
            fondo_comun: imp_bruto × 0.10.
            neto_honorario: imp_bruto − renta_cip − aporte_codemu − fondo_comun.
            honorario: Equals neto_honorario.

        Returns:
            Tuple of (ReciboHonorarioDelegado, created: bool).
        """
        return ReciboHonorarioDelegado.objects.get_or_create(
            liquidacion_delegado_id=liquidacion_delegado_id,
            defaults={
                "sub_total": sub_total,
                "imp_bruto": imp_bruto,
                "renta_cip": renta_cip,
                "aporte_codemu": aporte_codemu,
                "fondo_comun": fondo_comun,
                "neto_honorario": neto_honorario,
                "honorario": honorario,
            },
        )

    def list_recibos_paginated(
        self,
        page: int,
        page_size: int,
        delegado_id: int | None = None,
        liquidacion_id: int | None = None,
    ) -> tuple[list[ReciboHonorarioDelegado], int]:
        """
        List ReciboHonorarioDelegado records with pagination and optional filters.

        Applies select_related to avoid N+1 queries.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            delegado_id: Filter by liquidacion_delegado.delegado_id.
            liquidacion_id: Filter by liquidacion_delegado.liquidacion_id.

        Returns:
            Tuple of (list of ReciboHonorarioDelegado, total count).
        """
        qs = ReciboHonorarioDelegado.objects.select_related(
            "liquidacion_delegado",
            "liquidacion_delegado__delegado",
            "liquidacion_delegado__delegado__perfil_ingeniero",
            "liquidacion_delegado__especialidad_revision",
            "liquidacion_delegado__liquidacion",
            "liquidacion_delegado__liquidacion__proyecto",
            "liquidacion_delegado__liquidacion__municipalidad",
            "liquidacion_delegado__liquidacion__tipo_liquidacion",
        ).order_by("-created_at")

        if delegado_id is not None:
            qs = qs.filter(liquidacion_delegado__delegado_id=delegado_id)
        if liquidacion_id is not None:
            qs = qs.filter(liquidacion_delegado__liquidacion_id=liquidacion_id)

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total

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

    # ── ReciboHonorarioInspector ───────────────────────────────────────────────

    def crear_recibo_inspector(
        self,
        liquidacion_inspector_id,
        escala_descuento,
        inspecciones_programadas: int,
        costo_por_inspeccion: Decimal,
        inspecciones_mes: int,
        monto_bruto: Decimal,
        inspecciones_pagadas: int,
        saldo_inspecciones: int,
        sub_total: Decimal,
        tasa_descuento_aplicada: Decimal,
        descuento: Decimal,
        honorarios: Decimal,
    ) -> ReciboHonorarioInspector:
        """
        Create a ReciboHonorarioInspector with all pre-calculated fields.

        Args:
            liquidacion_inspector_id: FK a LiquidacionInspector.
            escala_descuento: EscalaDescuentoInspector vigente aplicada.
            inspecciones_programadas: cantidad_visitas de la liquidación.
            costo_por_inspeccion: importe_bruto / inspecciones_programadas.
            inspecciones_mes: Inspecciones liquidadas en el mes.
            monto_bruto: costo_por_inspeccion * inspecciones_mes.
            inspecciones_pagadas: Por ahora siempre 0.
            saldo_inspecciones: programadas - mes - pagadas.
            sub_total: Igual al monto_bruto.
            tasa_descuento_aplicada: Rango vigente según sub_total.
            descuento: sub_total * tasa_descuento_aplicada.
            honorarios: sub_total - descuento.

        Returns:
            ReciboHonorarioInspector instance.
        """
        return ReciboHonorarioInspector.objects.create(
            liquidacion_inspector_id=liquidacion_inspector_id,
            escala_descuento=escala_descuento,
            inspecciones_programadas=inspecciones_programadas,
            costo_por_inspeccion=costo_por_inspeccion,
            inspecciones_mes=inspecciones_mes,
            monto_bruto=monto_bruto,
            inspecciones_pagadas=inspecciones_pagadas,
            saldo_inspecciones=saldo_inspecciones,
            sub_total=sub_total,
            tasa_descuento_aplicada=tasa_descuento_aplicada,
            descuento=descuento,
            honorarios=honorarios,
        )

    def get_recibo_inspector_by_id(
        self, recibo_id
    ) -> Optional[ReciboHonorarioInspector]:
        """
        Get a ReciboHonorarioInspector by PK with related records loaded.

        Uses select_related to avoid N+1 when building the enriched result.

        Args:
            recibo_id: PK del ReciboHonorarioInspector.

        Returns:
            ReciboHonorarioInspector instance or None if not found.
        """
        return (
            ReciboHonorarioInspector.objects.select_related(
                "liquidacion_inspector",
                "liquidacion_inspector__inspector",
                "liquidacion_inspector__inspector__perfil_ingeniero",
                "liquidacion_inspector__especialidad_revision",
                "liquidacion_inspector__liquidacion",
                "liquidacion_inspector__liquidacion__liquidacion_general",
                "liquidacion_inspector__liquidacion__liquidacion_general__municipalidad",
                "liquidacion_inspector__liquidacion__liquidacion_general__proyecto",
                "liquidacion_inspector__liquidacion__liquidacion_general__tipo_liquidacion",
                "liquidacion_inspector__liquidacion__liquidacion_general__inspeccion_obra",
                "escala_descuento",
            )
            .filter(id=recibo_id)
            .first()
        )

    def list_recibos_inspectores_paginated(
        self,
        page: int,
        page_size: int,
        inspector_id=None,
        liquidacion_id=None,
    ) -> tuple[list[ReciboHonorarioInspector], int]:
        """
        List ReciboHonorarioInspector records with pagination and optional filters.

        Applies select_related to avoid N+1 queries.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            inspector_id: Filter by liquidacion_inspector.inspector_id.
            liquidacion_id: Filter by liquidacion_inspector.liquidacion.liquidacion_general_id.

        Returns:
            Tuple of (list of ReciboHonorarioInspector, total count).
        """
        qs = ReciboHonorarioInspector.objects.select_related(
            "liquidacion_inspector",
            "liquidacion_inspector__inspector",
            "liquidacion_inspector__inspector__perfil_ingeniero",
            "liquidacion_inspector__especialidad_revision",
            "liquidacion_inspector__liquidacion",
            "liquidacion_inspector__liquidacion__liquidacion_general",
            "liquidacion_inspector__liquidacion__liquidacion_general__municipalidad",
            "liquidacion_inspector__liquidacion__liquidacion_general__proyecto",
            "liquidacion_inspector__liquidacion__liquidacion_general__tipo_liquidacion",
            "liquidacion_inspector__liquidacion__liquidacion_general__inspeccion_obra",
            "escala_descuento",
        ).order_by("-created_at")

        if inspector_id is not None:
            qs = qs.filter(liquidacion_inspector__inspector_id=inspector_id)
        if liquidacion_id is not None:
            qs = qs.filter(
                liquidacion_inspector__liquidacion__liquidacion_general_id=liquidacion_id
            )

        total = qs.count()
        offset = (page - 1) * page_size
        objects = list(qs[offset:offset + page_size])
        return objects, total

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
        periodo: str,
    ) -> Optional[RegistroPagoInspector]:
        """
        Get a RegistroPagoInspector for a specific (IO, periodo) pair.

        Args:
            liquidacion_categoria_visitas_id: PK of the LiquidacionPorCategoriaVisitas.
            periodo: Period string in YYYY-MM format.

        Returns:
            RegistroPagoInspector instance or None if not found.
        """
        return (
            RegistroPagoInspector.objects
            .filter(
                liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
                periodo=periodo,
            )
            .first()
        )

    def upsert_registro_pago(
        self,
        liquidacion_categoria_visitas_id: int | str,
        periodo: str,
        inspecciones_pagadas: int,
    ) -> RegistroPagoInspector:
        """
        Create or update a RegistroPagoInspector, accumulating inspecciones_pagadas.

        Args:
            liquidacion_categoria_visitas_id: PK of the LiquidacionPorCategoriaVisitas.
            periodo: Period string in YYYY-MM format.
            inspecciones_pagadas: Number of inspections to add to the accumulated total.

        Returns:
            RegistroPagoInspector instance (created or updated).
        """
        registro, created = RegistroPagoInspector.objects.get_or_create(
            liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
            periodo=periodo,
            defaults={"inspecciones_pagadas": inspecciones_pagadas},
        )
        if not created:
            registro.inspecciones_pagadas += inspecciones_pagadas
            registro.save()
        return registro

    def crear_rh_inspector_mensual(
        self,
        inspector_id: int | str,
        periodo: str,
        escala_id: int | str,
        sub_total: Decimal,
        descuento: Decimal,
        honorarios: Decimal,
        inspector_operacion_id: int | str | None = None,
    ) -> ReciboHonorarioInspectorMensual:
        """
        Create a new ReciboHonorarioInspectorMensual (always creates, never reuses).

        Args:
            inspector_id: FK to Inspector.
            periodo: Period string in YYYY-MM format.
            escala_id: FK to EscalaDescuentoInspector.
            sub_total: Subtotal for the month.
            descuento: Discount amount.
            honorarios: Net honorarios to pay.
            inspector_operacion_id: Optional FK to InspectorOperacion (derived from selected items).

        Returns:
            Newly created ReciboHonorarioInspectorMensual instance.
        """
        return ReciboHonorarioInspectorMensual.objects.create(
            inspector_id=inspector_id,
            periodo=periodo,
            escala_descuento_id=escala_id,
            sub_total=sub_total,
            descuento=descuento,
            honorarios=honorarios,
            inspector_operacion_id=inspector_operacion_id,
        )

    def crear_detalle_honorario(
        self,
        recibo_mensual_id: int | str,
        liquidacion_categoria_visitas_id: int | str,
        inspecciones_liquidadas: int,
        costo_por_inspeccion: Decimal,
        monto_contribuido: Decimal,
    ) -> DetalleHonorarioInspector:
        """
        Create a DetalleHonorarioInspector record.

        Args:
            recibo_mensual_id: FK to ReciboHonorarioInspectorMensual.
            liquidacion_categoria_visitas_id: FK to LiquidacionPorCategoriaVisitas.
            inspecciones_liquidadas: Number of inspections liquidated in this detail.
            costo_por_inspeccion: Cost per inspection for this liquidacion.
            monto_contribuido: Monetary contribution from this liquidacion.

        Returns:
            DetalleHonorarioInspector instance.
        """
        return DetalleHonorarioInspector.objects.create(
            recibo_mensual_id=recibo_mensual_id,
            liquidacion_por_categoria_visitas_id=liquidacion_categoria_visitas_id,
            inspecciones_liquidadas=inspecciones_liquidadas,
            costo_por_inspeccion=costo_por_inspeccion,
            monto_contribuido=monto_contribuido,
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
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> list[dict]:
        """
        Get candidatas (LiquidacionInspector with remaining saldo) for an inspector.

        For each LiquidacionInspector assigned to the inspector:
        - Get LiquidacionPorCategoriaVisitas.cantidad_visitas (programadas)
        - Get accumulated RegistroPagoInspector for all periods < requested periodo,
          OR all periods if no periodo is supplied
        - Calculate saldo_disponible = programadas - pagadas_acumuladas
        - Return only those with saldo_disponible > 0

        Args:
            inspector_id: PK of the Inspector.
            periodo: Optional period string in YYYY-MM format.
                If provided, accumulates inspections paid in ALL periods strictly
                before this periodo. If None, accumulates all periods historically.
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
            # - If periodo is provided: all RegistroPagoInspector with periodo <= requested_periodo
            #   (includes current period's RegistroPagoInspector to prevent over-requesting)
            # - If no periodo: sum ALL periods (historical total)
            registro_qs = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas_id=lcv.id,
            )
            if periodo:
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

    def crear_rh_delegado_mensual(
        self,
        delegado_id: int | str,
        periodo: str,
        sub_total: Decimal,
        renta_cip: Decimal,
        aporte_codemu: Decimal,
        fondo_comun: Decimal,
        neto_honorario: Decimal,
        delegado_operacion_id: str | None = None,
    ) -> ReciboHonorarioDelegadoMensual:
        """
        Create a new ReciboHonorarioDelegadoMensual record.

        Always creates a new record — callers are responsible for ensuring
        no duplicate RH headers are created for the same delegation if that
        is not desired.

        Args:
            delegado_id: FK to Delegado.
            periodo: Period string in YYYY-MM format.
            sub_total: Subtotal for the month.
            renta_cip: 25% of sub_total.
            aporte_codemu: 5% of sub_total.
            fondo_comun: 10% of sub_total.
            neto_honorario: Net honorarios to pay.
            delegado_operacion_id: Optional FK to DelegadoOperacion.

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
                sub_total=sub_total,
                renta_cip=renta_cip,
                aporte_codemu=aporte_codemu,
                fondo_comun=fondo_comun,
                neto_honorario=neto_honorario,
            )
        else:
            return ReciboHonorarioDelegadoMensual.objects.create(
                delegado_id=(
                    int(delegado_id) if isinstance(delegado_id, str) else delegado_id
                ),
                periodo=periodo,
                sub_total=sub_total,
                renta_cip=renta_cip,
                aporte_codemu=aporte_codemu,
                fondo_comun=fondo_comun,
                neto_honorario=neto_honorario,
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
    ) -> DetalleHonorarioDelegado:
        """
        Create a DetalleHonorarioDelegado record.

        Args:
            recibo_mensual_id: FK to ReciboHonorarioDelegadoMensual.
            liquidacion_delegado_id: FK to LiquidacionDelegado.
            imp_bruto: Importe bruto from the LiquidacionPorcentajeObraDetalle.

        Returns:
            DetalleHonorarioDelegado instance.
        """
        return DetalleHonorarioDelegado.objects.create(
            recibo_mensual_id=recibo_mensual_id,
            liquidacion_delegado_id=liquidacion_delegado_id,
            imp_bruto=imp_bruto,
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
        delegado_id: int | None = None,
    ) -> tuple[list[ReciboHonorarioDelegadoMensual], int]:
        """
        List ReciboHonorarioDelegadoMensual records with pagination and optional filter.

        Prefetches detalles + liquidacion_delegado + liquidacion to avoid N+1.

        Args:
            page: 1-indexed page number.
            page_size: Elements per page.
            delegado_id: Filter by delegado_id.

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
                "detalles__liquidacion_delegado__liquidacion",
                "detalles__liquidacion_delegado__delegado_operacion",
            )
            .order_by("-periodo")
        )

        if delegado_id is not None:
            qs = qs.filter(delegado_id=delegado_id)

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
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito",
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito__provincia",
                "detalles__liquidacion_por_categoria_visitas__liquidacion_general__inspeccion_obra",
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
