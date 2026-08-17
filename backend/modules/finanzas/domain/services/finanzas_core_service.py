"""
FinanzasCoreService — ORM queries for finanzas entities.

Pure ORM access. No business logic.
"""
from datetime import date
from typing import Optional

from decimal import Decimal

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.recibo_honorario_inspector import (
    ReciboHonorarioInspector,
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