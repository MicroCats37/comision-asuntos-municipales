# -*- coding: utf-8 -*-
"""
RHReparticionEstacionalCoreService — sync DB operations for RH Reparticion Estacional.

Operations:
- Insert snapshot records (reparticion + detalles)
- Query fondo_comun sum from DetalleHonorarioDelegado
- Check for overlapping month ranges
- Query active reparticiones by especialidad/periodo
"""
from decimal import Decimal
from typing import Optional

from django.db.models import Sum

from modules.finanzas.domain.models.rh_reparticion_estacional import (
    RHReparticionEstacional,
    RHReparticionEstacionalDelegado,
    RHReparticionEstacionalCapitulo,
)

TWO_PLACES = Decimal("0.01")


def distribute_fondo_comun_cents(
    total: Decimal,
    capitulo_ids: list[int],
    delegado_ids: list[int],
) -> tuple[dict[int, Decimal], dict[int, Decimal], Decimal, Decimal]:
    """
    Distribute total_fondo_comun in exact integer cents.

    All leftover cents go to chapters first (deterministic order by ID ascending).
    Delegados never receive residual cents.

    Returns:
        (capitulo_amounts, delegado_amounts, monto_por_participacion_base, residual)

    Example:
        total=4.03, capitulo_ids=[1,2], delegado_ids=[10,11]
        - total_cents = 403
        - base_cents = 403 // 4 = 100
        - leftover = 403 % 4 = 3
        - extra_per_chapter = 3 // 2 = 1
        - remainder_to_first_chapters = 3 % 2 = 1
        - capitulo[1]: 100 + 1 + 1 = 102  (base + extra + 1 remainder)
        - capitulo[2]: 100 + 1 = 101       (base + extra only)
        - delegado[10] = 100
        - delegado[11] = 100
        - sum = 102+101+100+100 = 403 cents = 4.03 ✓
        - residual = 0.00 ✓
    """
    # Quantize total to 2 decimal places (what the DB stores)
    total_quantized = total.quantize(TWO_PLACES)
    total_cents = int(total_quantized * Decimal("100"))
    divisor_total = len(capitulo_ids) + len(delegado_ids)

    if divisor_total == 0:
        return {}, {}, Decimal("0.00"), total_quantized

    base_cents = total_cents // divisor_total
    leftover_cents = total_cents % divisor_total

    # Sort for deterministic order
    sorted_capitulo_ids = sorted(capitulo_ids)
    sorted_delegado_ids = sorted(delegado_ids)

    # Extra per chapter: distribute leftover evenly among chapters first
    extra_per_chapter = leftover_cents // len(capitulo_ids) if capitulo_ids else 0
    remainder_to_first_chapters = leftover_cents % len(capitulo_ids) if capitulo_ids else 0

    capitulo_amounts: dict[int, Decimal] = {}
    capitulo_counter = 0
    for cid in sorted_capitulo_ids:
        extra = extra_per_chapter
        if capitulo_counter < remainder_to_first_chapters:
            extra += 1
        capitulo_amounts[cid] = Decimal(base_cents + extra) / Decimal("100")
        capitulo_counter += 1

    # Delegados get exactly base — never extra
    delegado_amounts: dict[int, Decimal] = {}
    for did in sorted_delegado_ids:
        delegado_amounts[did] = Decimal(base_cents) / Decimal("100")

    monto_base = Decimal(base_cents) / Decimal("100")
    residual = Decimal("0.00")

    return capitulo_amounts, delegado_amounts, monto_base, residual


class RHReparticionEstacionalCoreService:
    """
    Core service for reparticion estacional — sync operations on ORM.

    No transaction.atomic() here — caller (flujo) provides it.
    """

    def get_fondo_comun_total(
        self,
        especialidad_revision_id: int,
        periodo: int,
        mes_desde: int,
        mes_hasta: int,
    ) -> Decimal:
        """
        Sum the fondo_comun from DetalleHonorarioDelegado records that match
        the given especialidad_revision and period/month range.

        Relationship path:
            DetalleHonorarioDelegado.liquidacion_delegado
                -> LiquidacionDelegado.periodo
                -> LiquidacionDelegado.mes
                -> LiquidacionDelegado.especialidad_revision

        Args:
            especialidad_revision_id: PK of EspecialidadRevision
            periodo: Year (e.g., 2026)
            mes_desde: Starting month (1-12)
            mes_hasta: Ending month (1-12)

        Returns:
            Sum of fondo_comun as Decimal, or Decimal("0.00") if none.
        """
        from modules.finanzas.domain.models import DetalleHonorarioDelegado

        result = (
            DetalleHonorarioDelegado.objects
            .filter(
                liquidacion_delegado__especialidad_revision_id=especialidad_revision_id,
                liquidacion_delegado__periodo=periodo,
                liquidacion_delegado__mes__gte=mes_desde,
                liquidacion_delegado__mes__lte=mes_hasta,
                fondo_comun__isnull=False,
            )
            .aggregate(total=Sum("fondo_comun"))
        )
        return result["total"] or Decimal("0.00")

    def get_capitulos_for_especialidad(
        self,
        especialidad_revision_id: int,
    ) -> list:
        """
        Get the list of Capitulo IDs linked to an EspecialidadRevision
        via EspecialidadRevisionCapitulo.

        Args:
            especialidad_revision_id: PK of EspecialidadRevision

        Returns:
            List of Capitulo IDs.
        """
        from modules.usuarios.domain.models.perfil_ingeniero import (
            EspecialidadRevisionCapitulo,
        )

        return list(
            EspecialidadRevisionCapitulo.objects
            .filter(especialidad_revision_id=especialidad_revision_id)
            .values_list("capitulo_id", flat=True)
        )

    def check_overlapping_reparticion(
        self,
        especialidad_revision_id: int,
        periodo: int,
        mes_desde: int,
        mes_hasta: int,
        exclude_id: Optional[str] = None,
    ) -> bool:
        """
        Check if there's an overlapping month range for the same
        especialidad_revision and periodo.

        Overlap exists when:
            existing.mes_desde <= new.mes_hasta AND existing.mes_hasta >= new.mes_desde

        Args:
            especialidad_revision_id: PK of EspecialidadRevision
            periodo: Year
            mes_desde: New range start month
            mes_hasta: New range end month
            exclude_id: Optional reparticion ID to exclude (for updates)

        Returns:
            True if overlap exists, False otherwise.
        """
        qs = RHReparticionEstacional.objects.filter(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
            is_deleted=False,
        )

        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        for reparticion in qs:
            # Check overlap: existing.mes_desde <= new.mes_hasta AND existing.mes_hasta >= new.mes_desde
            if reparticion.mes_desde <= mes_hasta and reparticion.mes_hasta >= mes_desde:
                return True
        return False

    def get_active_reparticiones(
        self,
        especialidad_revision_id: Optional[int] = None,
        periodo: Optional[int] = None,
    ):
        """
        Query active (non-deleted) reparticiones, optionally filtered.

        Args:
            especialidad_revision_id: Optional filter by EspecialidadRevision
            periodo: Optional filter by year

        Returns:
            QuerySet of RHReparticionEstacional
        """
        qs = RHReparticionEstacional.objects.filter(is_deleted=False)
        if especialidad_revision_id is not None:
            qs = qs.filter(especialidad_revision_id=especialidad_revision_id)
        if periodo is not None:
            qs = qs.filter(periodo=periodo)
        return qs.order_by("-periodo", "-created_at")

    def get_reparticion_by_id(self, reparticion_id: str) -> Optional[RHReparticionEstacional]:
        """
        Get a reparticion by ID with related objects prefetched.

        Prefetches detalles_delegados->delegado->perfil_ingeniero and
        detalles_capitulos->capitulo to avoid N+1 when building nested results.
        """
        return (
            RHReparticionEstacional.objects
            .select_related("especialidad_revision")
            .prefetch_related(
                "detalles_delegados__delegado__perfil_ingeniero",
                "detalles_capitulos__capitulo",
            )
            .filter(id=reparticion_id)
            .first()
        )

    def create_reparticion(
        self,
        especialidad_revision_id: int,
        periodo: int,
        total_fondo_comun: Decimal,
        numero_capitulos: int,
        numero_delegados: int,
        monto_por_participacion: Decimal,
        residual: Decimal,
        mes_desde: int,
        mes_hasta: int,
    ) -> RHReparticionEstacional:
        """
        Create a new RHReparticionEstacional snapshot.

        Args:
            All fields from the reparticion header.

        Returns:
            Created RHReparticionEstacional instance.
        """
        return RHReparticionEstacional.objects.create(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
            total_fondo_comun=total_fondo_comun,
            numero_capitulos=numero_capitulos,
            numero_delegados=numero_delegados,
            monto_por_participacion=monto_por_participacion,
            residual=residual,
            mes_desde=mes_desde,
            mes_hasta=mes_hasta,
        )

    def create_detalle_delegado(
        self,
        reparticion: RHReparticionEstacional,
        delegado_id: int,
        monto: Decimal,
    ) -> RHReparticionEstacionalDelegado:
        """Create a detalle delegado for a reparticion."""
        return RHReparticionEstacionalDelegado.objects.create(
            reparticion=reparticion,
            delegado_id=delegado_id,
            monto=monto,
        )

    def create_detalle_capitulo(
        self,
        reparticion: RHReparticionEstacional,
        capitulo_id: int,
        monto: Decimal,
    ) -> RHReparticionEstacionalCapitulo:
        """Create a detalle capitulo for a reparticion."""
        return RHReparticionEstacionalCapitulo.objects.create(
            reparticion=reparticion,
            capitulo_id=capitulo_id,
            monto=monto,
        )

    def soft_delete_reparticion(self, reparticion: RHReparticionEstacional) -> None:
        """Soft-delete a reparticion."""
        from django.utils import timezone
        reparticion.is_deleted = True
        reparticion.deleted_at = timezone.now()
        reparticion.save(update_fields=["is_deleted", "deleted_at"])