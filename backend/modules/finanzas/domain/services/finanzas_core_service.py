"""
FinanzasCoreService — ORM queries for finanzas entities.

Pure ORM access. No business logic.
"""
from typing import Optional

from decimal import Decimal

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado


class FinanzasCoreService:
    """
    Core service for querying IGV, UIT, and ReciboHonorarioDelegado records.
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