"""
InspectorCoreService — pure ORM operations for Inspector.

NO business logic. Only: list, get, filter.
"""
from datetime import date
from typing import Optional
import uuid
from django.db.models import Prefetch, Q

from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorAsignacionPeriodo,
    InspectorTipoLiquidacion,
)


class InspectorCoreService:
    """
    Core sync service for Inspector ORM operations.
    Pure ORM — no business logic.
    """

    def list_inspectores_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated Inspector queryset.
        Uses select_related to avoid N+1 on perfil_ingeniero.
        Uses prefetch_related to load tipos_liquidacion (catalog data moved from Inspector).
        Returns (queryset, total_count).
        """
        qs = Inspector.objects.select_related(
            'perfil_ingeniero',
        ).prefetch_related(
            Prefetch(
                'tipos_liquidacion',
                queryset=InspectorTipoLiquidacion.objects.select_related('tipo_liquidacion'),
            ),
        ).order_by(
            'perfil_ingeniero__apellido_paterno',
            'perfil_ingeniero__apellido_materno',
            'perfil_ingeniero__nombres',
        )

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def get_inspector_by_id(self, inspector_id: uuid.UUID) -> Optional[Inspector]:
        """
        Returns a single Inspector by UUID.
        Prefetches tipos_liquidacion for catalog data access.
        Returns None if not found.
        """
        return Inspector.objects.select_related(
            'perfil_ingeniero',
        ).prefetch_related(
            Prefetch(
                'tipos_liquidacion',
                queryset=InspectorTipoLiquidacion.objects.select_related('tipo_liquidacion'),
            ),
        ).filter(id=inspector_id).first()

    def list_inspectores_vigentes(
        self,
        tipo_liquidacion: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple:
        """
        Returns all Inspectores with at least one vigente InspectorAsignacionPeriodo,
        filtered by tipo_liquidacion (now through InspectorTipoLiquidacion).

        vigentes: periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today)

        Returns (list[Inspector], total).
        """
        today = date.today()
        qs = Inspector.objects.filter(
            tipos_liquidacion__tipo_liquidacion__codigo=tipo_liquidacion,
            tipos_liquidacion__periodos__periodo_inicio__lte=today,
        ).filter(
            Q(tipos_liquidacion__periodos__periodo_fin__isnull=True)
            | Q(tipos_liquidacion__periodos__periodo_fin__gte=today)
        ).select_related(
            'perfil_ingeniero',
        ).prefetch_related(
            Prefetch(
                'tipos_liquidacion',
                queryset=InspectorTipoLiquidacion.objects.select_related(
                    'tipo_liquidacion',
                ).prefetch_related('periodos'),
            ),
        ).order_by(
            'perfil_ingeniero__apellido_paterno',
            'perfil_ingeniero__apellido_materno',
            'perfil_ingeniero__nombres',
        ).distinct()

        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset:offset + page_size]), total
