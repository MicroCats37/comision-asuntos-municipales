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
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.models.registro_pago_inspector import (
    RegistroPagoInspector,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
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
    ) -> tuple[ReciboHonorarioInspectorMensual, bool]:
        """
        Create or retrieve a ReciboHonorarioInspectorMensual for (inspector, periodo).

        Args:
            inspector_id: FK to Inspector.
            periodo: Period string in YYYY-MM format.
            escala_id: FK to EscalaDescuentoInspector.
            sub_total: Subtotal for the month.
            descuento: Discount amount.
            honorarios: Net honorarios to pay.

        Returns:
            Tuple of (ReciboHonorarioInspectorMensual, created: bool).
        """
        return ReciboHonorarioInspectorMensual.objects.get_or_create(
            inspector_id=inspector_id,
            periodo=periodo,
            defaults={
                "escala_descuento_id": escala_id,
                "sub_total": sub_total,
                "descuento": descuento,
                "honorarios": honorarios,
            },
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