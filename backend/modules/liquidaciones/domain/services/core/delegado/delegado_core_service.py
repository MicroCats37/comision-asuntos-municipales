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
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionEspecialidadDisponibles,
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
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        capitulo_id: Optional[uuid.UUID] = None,
        especialidad_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Returns paginated Delegado queryset with optional filters.
        Uses select_related/prefetch_related to avoid N+1.
        Returns (queryset, total_count).
        """
        qs = Delegado.objects.select_related(
            'perfil_ingeniero',
            'perfil_ingeniero__especialidad',
            'perfil_ingeniero__capitulo',
        ).prefetch_related(
            'municipalidades_asignadas',
            'municipalidades_asignadas__municipalidad',
            'municipalidades_asignadas__periodos',
        ).order_by(
            'perfil_ingeniero__apellido_paterno',
            'perfil_ingeniero__apellido_materno',
            'perfil_ingeniero__nombres',
        )

        if cip:
            qs = qs.filter(perfil_ingeniero__cip__icontains=cip)
        if municipalidad_id:
            qs = qs.filter(municipalidades_asignadas__municipalidad_id=municipalidad_id)
        if capitulo_id:
            qs = qs.filter(perfil_ingeniero__capitulo_id=capitulo_id)
        if especialidad_id:
            qs = qs.filter(perfil_ingeniero__especialidad_id=especialidad_id)

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
        Returns all DelegadoOperacion records for a delegado,
        with their current periodo vigentes.
        """
        return list(
            DelegadoOperacion.objects.filter(
                delegado_id=delegado_id
            ).select_related(
                'delegado__perfil_ingeniero',
                'municipalidad',
            ).prefetch_related(
                'periodos',
            )
        )

    def _is_vigente(self, periodo: DelegadoOperacionPeriodo, today: date) -> bool:
        """Check if a periodo is vigente (active on given date)."""
        return periodo.periodo_inicio <= today and (
            periodo.periodo_fin is None or periodo.periodo_fin >= today
        )

    def _get_current_periodo(
        self, municipalidad: DelegadoOperacion, today: date
    ) -> Optional[DelegadoOperacionPeriodo]:
        """Returns the current vigente periodo for a DelegadoOperacion, or None."""
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
        Returns all DelegadoOperacion records for a municipalidad.
        If vigente=True, filters to only current periods (periodo_inicio <= today AND
        (periodo_fin IS NULL OR periodo_fin >= today)).
        Returns (list[DelegadoOperacion], total).
        """
        qs = DelegadoOperacion.objects.filter(
            municipalidad_id=municipalidad_id
        ).select_related(
            'delegado__perfil_ingeniero',
            'municipalidad',
        ).prefetch_related(
            'periodos',
        )

        if vigente is not None:
            # Normalize string→bool from query params
            if isinstance(vigente, str):
                vigente = vigente.lower() == "true"
            if vigente:
                today = date.today()
                qs = qs.filter(
                    Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__isnull=True)
                    | Q(periodos__periodo_inicio__lte=today, periodos__periodo_fin__gte=today)
                )

        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset:offset + page_size]), total

    def get_liquidacion_general_by_id(
        self,
        liquidacion_id: uuid.UUID,
    ) -> Optional[LiquidacionGeneral]:
        """
        Returns a single LiquidacionGeneral by UUID.
        Returns None if not found.
        """
        return LiquidacionGeneral.objects.filter(id=liquidacion_id).select_related(
            "tipo_liquidacion",
            "municipalidad",
        ).first()

    def list_especialidad_ids_vigentes_para_tipo(
        self,
        tipo_codigo: str,
        fecha: date,
    ) -> list:
        """
        Returns string especialidad_ids of vigentes LiquidacionEspecialidadDisponibles
        for the given tipo_liquidacion codigo on the given date.
        Vigente: activo=True AND periodo_inicio <= fecha AND
        (periodo_fin IS NULL OR periodo_fin >= fecha).
        """
        return [
            str(especialidad_id)
            for especialidad_id in LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion__codigo=tipo_codigo,
                activo=True,
                periodo_inicio__lte=fecha,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
            ).values_list("especialidad_id", flat=True)
        ]

    def list_delegados_vigentes(
        self,
        municipalidad_id: uuid.UUID,
        tipo_codigo: str,
        fecha: date,
    ) -> list:
        """
        Returns DelegadoOperacion candidates matching a liquidación tipo.

        Match:
        1. DelegadoOperacion with municipalidad_id AND
           (liquidacion_revision IS NULL OR liquidacion_revision.codigo == tipo_codigo)
        2. operacion.especialidad_revision IN especialidades vigentes del tipo
        3. periodo municipal vigente (inicio <= fecha AND fin IS NULL OR >= fecha)
        """
        especialidad_ids = self.list_especialidad_ids_vigentes_para_tipo(tipo_codigo, fecha)
        return list(
            DelegadoOperacion.objects.filter(
                municipalidad_id=municipalidad_id,
            ).filter(
                Q(liquidacion_revision__isnull=True)
                | Q(liquidacion_revision__codigo=tipo_codigo)
            ).filter(
                especialidad_revision_id__in=especialidad_ids,
            ).filter(
                Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__isnull=True,
                )
                | Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__gte=fecha,
                )
            ).select_related(
                "delegado__perfil_ingeniero",
                "especialidad_revision",
            ).prefetch_related(
                "periodos",
            ).distinct().order_by(
                "delegado__perfil_ingeniero__apellido_paterno",
                "delegado__perfil_ingeniero__apellido_materno",
                "delegado__perfil_ingeniero__nombres",
            )
        )

    def get_asignacion_municipal_vigente(
        self,
        delegado_id: uuid.UUID,
        municipalidad_id: uuid.UUID,
        fecha: date,
    ) -> Optional[DelegadoOperacion]:
        """
        Returns the DelegadoOperacion for (delegado, municipalidad) with a
        vigente periodo on the given date, or None.
        """
        return (
            DelegadoOperacion.objects.filter(
                delegado_id=delegado_id,
                municipalidad_id=municipalidad_id,
            ).filter(
                Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__isnull=True,
                )
                | Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__gte=fecha,
                )
            ).distinct().first()
        )

    def crear_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
        especialidad_revision,
        **kwargs,
    ) -> LiquidacionDelegado:
        """Creates a LiquidacionDelegado association (pure ORM wrapper)."""
        return LiquidacionDelegado.objects.create(
            liquidacion=liquidacion,
            delegado=delegado,
            especialidad_revision=especialidad_revision,
            **kwargs,
        )

    def get_operacion_vigente_para_liquidacion(
        self,
        delegado,
        liquidacion,
        fecha=None,
    ) -> Optional[DelegadoOperacion]:
        """
        Returns the vigente DelegadoOperacion for (delegado, municipalidad, tipo)
        matching the liquidacion, or None.

        La especialidad_revision ahora vive en la operación — este método resuelve
        cuál aplicar según la municipalidad + tipo_liquidacion de la liquidación.
        """
        if fecha is None:
            from django.utils import timezone
            fecha = timezone.localdate()
        return (
            DelegadoOperacion.objects.filter(
                delegado=delegado,
                municipalidad_id=liquidacion.municipalidad_id,
            ).filter(
                Q(liquidacion_revision__isnull=True)
                | Q(liquidacion_revision_id=liquidacion.tipo_liquidacion_id)
            ).filter(
                Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__isnull=True,
                )
                | Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__gte=fecha,
                )
            ).select_related(
                "especialidad_revision",
            ).distinct().first()
        )

    def actualizar_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
        **campos,
    ) -> Optional[LiquidacionDelegado]:
        """
        Updates metadata fields of a LiquidacionDelegado association.
        Returns the updated instance, or None if the association does not exist.
        """
        asociacion = LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion, delegado=delegado
        ).first()
        if not asociacion:
            return None
        for campo, valor in campos.items():
            setattr(asociacion, campo, valor)
        asociacion.save()
        return asociacion

    def eliminar_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
    ) -> tuple:
        """Deletes the LiquidacionDelegado association for (liquidacion, delegado)."""
        return LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion, delegado=delegado
        ).delete()

    def obtener_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
    ) -> Optional[LiquidacionDelegado]:
        """
        Returns the LiquidacionDelegado association for (liquidacion, delegado),
        or None.
        """
        return LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion, delegado=delegado,
        ).select_related(
            "delegado__perfil_ingeniero",
            "especialidad_revision",
        ).first()

    def list_liquidacion_delegado_paginated(
        self,
        page: int,
        page_size: int,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Returns paginated LiquidacionDelegado queryset with optional filters.
        Uses select_related to avoid N+1: liquidacion, liquidacion__proyecto,
        liquidacion__municipalidad, liquidacion__tipo_liquidacion, delegado,
        delegado__perfil_ingeniero, especialidad_revision.
        Returns (queryset_list, total_count).
        """
        qs = LiquidacionDelegado.objects.select_related(
            "liquidacion__proyecto",
            "liquidacion__municipalidad",
            "liquidacion__tipo_liquidacion",
            "delegado__perfil_ingeniero",
            "especialidad_revision",
        ).order_by("-liquidacion__fecha_registro")

        if cip:
            qs = qs.filter(delegado__perfil_ingeniero__cip__icontains=cip)
        if liquidacion_id:
            qs = qs.filter(liquidacion_id=liquidacion_id)

        total = qs.count()
        offset = (page - 1) * page_size
        return list(qs[offset:offset + page_size]), total
