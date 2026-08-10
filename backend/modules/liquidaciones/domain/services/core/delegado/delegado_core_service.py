"""
DelegadoCoreService — pure ORM operations for Delegado.

NO business logic. Only: list, get, filter.
"""
from datetime import date
from typing import Optional
import uuid
from django.db.models import Q

from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
)


class DelegadoCoreService:
    """
    Core sync service for Delegado ORM operations.
    Pure ORM — no business logic.
    """

    def list_delegados_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated Delegado queryset.
        Uses select_related to avoid N+1 on perfil_ingeniero.
        Returns (queryset, total_count).
        """
        qs = Delegado.objects.select_related(
            'perfil_ingeniero',
        ).order_by(
            'perfil_ingeniero__apellido_paterno',
            'perfil_ingeniero__apellido_materno',
            'perfil_ingeniero__nombres',
        )

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def get_delegado_by_id(self, delegado_id: uuid.UUID) -> Optional[Delegado]:
        """
        Returns a single Delegado by UUID.
        Returns None if not found.
        """
        return Delegado.objects.select_related(
            'perfil_ingeniero',
        ).filter(id=delegado_id).first()

    def get_municipalidades_for_delegado(
        self,
        delegado_id: uuid.UUID,
    ) -> list:
        """
        Returns all DelegadoMunicipalidad records for a delegado,
        with their current periodo vigentes.
        """
        return list(
            DelegadoMunicipalidad.objects.filter(
                delegado_id=delegado_id
            ).select_related(
                'delegado__perfil_ingeniero',
                'municipalidad',
            ).prefetch_related(
                'periodos',
            )
        )

    def _is_vigente(self, periodo: DelegadoMunicipalidadPeriodo, today: date) -> bool:
        """Check if a periodo is vigente (active on given date)."""
        return periodo.periodo_inicio <= today and (
            periodo.periodo_fin is None or periodo.periodo_fin >= today
        )

    def _get_current_periodo(
        self, municipalidad: DelegadoMunicipalidad, today: date
    ) -> Optional[DelegadoMunicipalidadPeriodo]:
        """Returns the current vigente periodo for a DelegadoMunicipalidad, or None."""
        periodos = list(municipalidad.periodos.all())
        for periodo in periodos:
            if self._is_vigente(periodo, today):
                return periodo
        return None

    def get_delegados_for_municipalidad(
        self,
        municipalidad_id: uuid.UUID,
        vigente: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple:
        """
        Returns all DelegadoMunicipalidad records for a municipalidad.
        If vigente=True, filters to only current periods (periodo_inicio <= today AND
        (periodo_fin IS NULL OR periodo_fin >= today)).
        Returns (list[DelegadoMunicipalidad], total).
        """
        qs = DelegadoMunicipalidad.objects.filter(
            municipalidad_id=municipalidad_id
        ).select_related(
            'delegado__perfil_ingeniero',
            'municipalidad',
        ).prefetch_related(
            'periodos',
        )

        if vigente is not None:
            today = date.today()
            if vigente:
                qs = qs.filter(
                    Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__isnull=True)
                    | Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__gte=today)
                )
            else:
                # Get all vigente IDs and exclude them
                vigentes_ids = list(
                    DelegadoMunicipalidad.objects.filter(
                        municipalidad_id=municipalidad_id
                    ).filter(
                        Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__isnull=True)
                        | Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__gte=today)
                    ).values_list('id', flat=True)
                )

                qs = qs.exclude(id__in=vigentes_ids)

        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset:offset + page_size]), total
