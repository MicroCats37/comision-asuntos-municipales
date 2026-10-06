"""
InspectorCoreService — operaciones ORM puras para Inspector.

SIN lógica de negocio. Solo: listar, obtener, filtrar.
"""
from datetime import date
from typing import Optional
import uuid
from django.db.models import Prefetch, Q

from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
    LiquidacionInspector,
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
                queryset=InspectorOperacion.objects.select_related('tipo_liquidacion'),
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
                queryset=InspectorOperacion.objects.select_related('tipo_liquidacion'),
            ),
        ).filter(id=inspector_id).first()

    def list_inspectores_vigentes(
        self,
        tipo_liquidacion: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple:
        """
        Returns all Inspectores with at least one vigente InspectorOperacionPeriodo,
        filtered by tipo_liquidacion (now through InspectorOperacion).

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
                queryset=InspectorOperacion.objects.select_related(
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

    def list_inspectores_vigentes_para_tipo(
        self,
        tipo_liquidacion: str,
        fecha: Optional[date] = None,
        categoria: Optional[str] = None,
        q: Optional[str] = None,
    ) -> list:
        """
        Returns InspectorOperacion candidates vigentes para un tipo de liquidación.

        Match (igual al alpha, ahora sobre el refactor):
        1. operacion.tipo_liquidacion.codigo == tipo_liquidacion
        2. operacion.especialidad_revision NOT NULL (siempre lo es en el refactor)
        3. periodo vigente (periodo_inicio <= fecha AND (fin IS NULL OR fin >= fecha))

        Filtros opcionales para el form de creación IO:
        - categoria: coincidencia en operacion.categoria
        - q: búsqueda por nombre/CIP (icontains)

        Returns: list[InspectorOperacion] con select_related de perfil/especialidad/tipo.
        """
        if fecha is None:
            from django.utils import timezone
            fecha = timezone.localdate()

        qs = InspectorOperacion.objects.filter(
            tipo_liquidacion__codigo=tipo_liquidacion,
        ).filter(
            Q(
                periodos__periodo_inicio__lte=fecha,
                periodos__periodo_fin__isnull=True,
            )
            | Q(
                periodos__periodo_inicio__lte=fecha,
                periodos__periodo_fin__gte=fecha,
            )
        )

        if categoria:
            qs = qs.filter(categoria=categoria)
        if q:
            qs = qs.filter(
                Q(inspector__perfil_ingeniero__nombres__icontains=q)
                | Q(inspector__perfil_ingeniero__apellido_paterno__icontains=q)
                | Q(inspector__perfil_ingeniero__apellido_materno__icontains=q)
                | Q(inspector__perfil_ingeniero__cip__icontains=q)
            )

        return list(
            qs.select_related(
                "inspector__perfil_ingeniero",
                "especialidad_revision",
                "tipo_liquidacion",
            ).prefetch_related(
                "periodos",
            ).distinct().order_by(
                "inspector__perfil_ingeniero__apellido_paterno",
                "inspector__perfil_ingeniero__apellido_materno",
                "inspector__perfil_ingeniero__nombres",
            )
        )

    def list_liquidacion_inspector_paginated(
        self,
        page: int,
        page_size: int,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Returns paginated LiquidacionInspector queryset with optional filters.

        select_related para evitar N+1:
        liquidacion__liquidacion_general, inspector__perfil_ingeniero, especialidad_revision.

        Returns (queryset_list, total_count).
        """
        qs = (
            LiquidacionInspector.objects.select_related(
                "liquidacion__liquidacion_general__proyecto",
                "liquidacion__liquidacion_general__municipalidad",
                "liquidacion__liquidacion_general__tipo_liquidacion",
                "inspector__perfil_ingeniero",
                "especialidad_revision",
            )
            .order_by("-liquidacion__liquidacion_general__fecha_registro")
        )

        if cip:
            qs = qs.filter(inspector__perfil_ingeniero__cip__icontains=cip)
        if liquidacion_id:
            qs = qs.filter(liquidacion__liquidacion_general_id=liquidacion_id)

        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset:offset + page_size]), total

    def get_inspector_operacion_by_id(
        self,
        inspector_operacion_id: uuid.UUID,
    ) -> Optional[InspectorOperacion]:
        """
        Returns a single InspectorOperacion by UUID.
        Returns None if not found.
        """
        return InspectorOperacion.objects.filter(id=inspector_operacion_id).first()

    def crear_liquidacion_inspector(
        self,
        liquidacion,
        inspector_id: uuid.UUID,
        inspector_operacion,
    ) -> LiquidacionInspector:
        """
        Creates a LiquidacionInspector association.

        The inspector_operacion FK is set directly (not derived from inspector).
        The FK was added in migration 0033.
        """
        inspector = Inspector.objects.get(id=inspector_id)
        return LiquidacionInspector.objects.create(
            liquidacion=liquidacion,
            inspector=inspector,
            inspector_operacion=inspector_operacion,
            especialidad_revision=inspector_operacion.especialidad_revision,
        )

    def get_liquidacion_inspector_by_ids(
        self,
        liquidacion_id: str,
        inspector_id: str,
    ) -> Optional[LiquidacionInspector]:
        """
        Returns a LiquidacionInspector by liquidacion_id and inspector_id.
        """
        return LiquidacionInspector.objects.filter(
            liquidacion_id=liquidacion_id,
            inspector_id=inspector_id,
        ).select_related(
            "inspector__perfil_ingeniero",
            "especialidad_revision",
        ).first()

    def eliminar_liquidacion_inspector(
        self,
        liquidacion,
        inspector_id: uuid.UUID,
    ) -> None:
        """
        Deletes a LiquidacionInspector association by liquidacion and inspector_id.
        """
        LiquidacionInspector.objects.filter(
            liquidacion=liquidacion,
            inspector_id=inspector_id,
        ).delete()

    def obtener_liquidacion_inspector(
        self,
        liquidacion,
        inspector,
    ) -> Optional[LiquidacionInspector]:
        """
        Returns a LiquidacionInspector for the given liquidacion and inspector.
        """
        return LiquidacionInspector.objects.filter(
            liquidacion=liquidacion,
            inspector=inspector,
        ).first()
