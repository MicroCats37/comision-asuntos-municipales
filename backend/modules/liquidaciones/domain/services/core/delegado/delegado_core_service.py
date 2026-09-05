"""
DelegadoCoreService — pure ORM operations for Delegado.

NO business logic. Only: list, get, filter.
"""
from datetime import date
from typing import Optional
import uuid
from django.db.models import Q, Exists, OuterRef

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
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.results.delegado.delegado_result import (
    MunicipalidadesAsignadasResult,
    MunicipalidadBasicResult,
    DelegadoForMunicipalidadResult,
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

    def get_delegado_operacion_by_id(
        self,
        operacion_id: uuid.UUID,
    ) -> Optional[DelegadoOperacion]:
        """
        Returns a single DelegadoOperacion by UUID with prefetched relations.
        Returns None if not found.
        """
        return (
            DelegadoOperacion.objects.filter(id=operacion_id)
            .select_related(
                'delegado__perfil_ingeniero',
                'municipalidad',
                'especialidad_revision',
                'tipo_liquidacion',
            )
            .prefetch_related('periodos')
            .first()
        )

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

    def build_municipalidad_asignada_result(
        self, dm: DelegadoOperacion, today: date
    ) -> MunicipalidadesAsignadasResult:
        """
        Builds MunicipalidadesAsignadasResult from a DelegadoOperacion ORM object.
        Encapsulates iteration over dm.periodos.all() to find the current periodo.
        """
        current_periodo = self._get_current_periodo(dm, today)
        return MunicipalidadesAsignadasResult(
            id=str(dm.id),
            municipalidad=MunicipalidadBasicResult(
                id=str(dm.municipalidad.id),
                codigo=dm.municipalidad.codigo,
                nombre=dm.municipalidad.nombre,
            ),
            tipo=dm.tipo or "",
            periodo_inicio=current_periodo.periodo_inicio if current_periodo else None,
            periodo_fin=current_periodo.periodo_fin if current_periodo else None,
            es_vigente=current_periodo is not None,
        )

    def build_delegado_for_municipalidad_result(
        self, dm: DelegadoOperacion, today: date
    ) -> DelegadoForMunicipalidadResult:
        """
        Builds DelegadoForMunicipalidadResult from a DelegadoOperacion ORM object.
        Encapsulates iteration over dm.periodos.all() to find the current periodo.
        """
        from modules.liquidaciones.domain.results.delegado.delegado_result import PerfilIngenieroResult
        
        current_periodo = self._get_current_periodo(dm, today)
        
        # Build perfil_ingeniero result
        perfil = dm.delegado.perfil_ingeniero
        especialidad_result = None
        if getattr(perfil, "especialidad", None):
            from modules.liquidaciones.domain.results.delegado.delegado_result import EspecialidadResult
            especialidad_result = EspecialidadResult(
                id=str(perfil.especialidad.id),
                codigo=perfil.especialidad.codigo,
                nombre=perfil.especialidad.nombre,
            )
        capitulo_result = None
        if getattr(perfil, "capitulo", None):
            from modules.liquidaciones.domain.results.delegado.delegado_result import CapituloResult
            capitulo_result = CapituloResult(
                id=str(perfil.capitulo.id),
                registro_id=perfil.capitulo.registro_id,
                abreviacion=perfil.capitulo.abreviacion,
                nombre=perfil.capitulo.nombre,
            )
        
        perfil_result = PerfilIngenieroResult(
            id=str(perfil.id),
            cip=perfil.cip or "",
            dni=perfil.dni or "",
            nombres=perfil.nombres or "",
            apellido_paterno=perfil.apellido_paterno or "",
            apellido_materno=perfil.apellido_materno or "",
            nombre_completo=perfil.nombre_completo,
            correo_personal=perfil.correo_personal,
            correo_institucional=perfil.correo_institucional,
            especialidad=especialidad_result,
            capitulo=capitulo_result,
        )
        
        return DelegadoForMunicipalidadResult(
            id=str(dm.delegado.id),
            perfil_ingeniero=perfil_result,
            tipo=dm.tipo or "",
            periodo_inicio=current_periodo.periodo_inicio if current_periodo else None,
            periodo_fin=current_periodo.periodo_fin if current_periodo else None,
            es_vigente=current_periodo is not None,
        )

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
           (tipo_liquidacion IS NULL OR tipo_liquidacion.codigo == tipo_codigo)
        2. operacion.especialidad_revision IN especialidades vigentes del tipo
        3. periodo municipal vigente (inicio <= fecha AND fin IS NULL OR >= fecha)
        """
        especialidad_ids = self.list_especialidad_ids_vigentes_para_tipo(tipo_codigo, fecha)
        return list(
            DelegadoOperacion.objects.filter(
                municipalidad_id=municipalidad_id,
            ).filter(
                Q(tipo_liquidacion__isnull=True)
                | Q(tipo_liquidacion__codigo=tipo_codigo)
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
                Q(tipo_liquidacion__isnull=True)
                | Q(tipo_liquidacion_id=liquidacion.tipo_liquidacion_id)
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

    def resolve_delegado_operacion(
        self,
        delegado: Delegado,
        municipalidad_id: uuid.UUID,
        tipo_liquidacion_id: uuid.UUID,
        tipo_delegado: str,
        fecha: date,
    ) -> Optional[DelegadoOperacion]:
        """
        Resolves exactly ONE active DelegadoOperacion matching:
          cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + current vigency.

        Resolution logic:
        1. Find all active operations for (delegado, municipalidad, tipo_delegado) with vigente periodo.
        2. Among those, match on tipo_liquidacion:
           - If an operation has tipo_liquidacion_id matching tipo_liquidacion_id exactly -> use it.
           - If an operation has tipo_liquidacion_id=None (wildcard) -> it's a candidate.
        3. If both exact match AND wildcard match -> 409 conflict (ambiguity).
        4. If only wildcard matches -> use the wildcard.
        5. If only exact match -> use the exact.
        6. If neither matches -> 404.

        Returns:
            The resolved DelegadoOperacion.

        Raises:
            HttpError 404: No matching operation found.
            HttpError 409: Ambiguous match (both wildcard and exact match).
        """
        from ninja.errors import HttpError
        from modules.liquidaciones.domain.constants import TipoDelegado

        # Get all active operations for this delegado/municipalidad/tipo with vigente periodo
        active_ops = list(
            DelegadoOperacion.objects.filter(
                delegado=delegado,
                municipalidad_id=municipalidad_id,
                tipo=tipo_delegado,
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
                "municipalidad",
                "especialidad_revision",
                "tipo_liquidacion",
            ).distinct()
        )

        if not active_ops:
            raise HttpError(404, "No se encontró operación activa para los criterios dados")

        # Separate into exact match (tipo_liquidacion == tipo_liquidacion_id) and wildcard (null)
        exact_matches = [op for op in active_ops if op.tipo_liquidacion_id == tipo_liquidacion_id]
        wildcard_matches = [op for op in active_ops if op.tipo_liquidacion_id is None]

        # Case: both exact and wildcard exist -> ambiguity -> 409
        if exact_matches and wildcard_matches:
            raise HttpError(409, "Configuración ambigua: existe operación wildcard y específica para este tipo de liquidación")

        # Case: exact match exists
        if exact_matches:
            if len(exact_matches) > 1:
                raise HttpError(409, "Múltiples operaciones activas coinciden con los criterios")
            return exact_matches[0]

        # Case: wildcard match exists
        if wildcard_matches:
            if len(wildcard_matches) > 1:
                raise HttpError(409, "Múltiples operaciones wildcard coinciden con los criterios")
            return wildcard_matches[0]

        # Case: no match found
        raise HttpError(404, "No se encontró operación activa para los criterios dados")

    def get_operatividades_vigentes_delegado(
        self,
        delegado: Delegado,
        fecha: date,
    ) -> list:
        """
        Returns all active DelegadoOperacion records for a delegado that have
        a vigente periodo on the given date.

        Each record includes the current periodo's vigency dates.

        Args:
            delegado: The Delegado ORM object.
            fecha: Reference date for vigencia checks.

        Returns:
            List of DelegadoOperacion ORM objects with prefetched relations.
        """
        return list(
            DelegadoOperacion.objects.filter(
                delegado=delegado,
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
                "municipalidad",
                "tipo_liquidacion",
                "especialidad_revision",
            ).prefetch_related(
                "periodos",
            ).distinct().order_by(
                "municipalidad__nombre",
            )
        )

    def get_candidatas_for_delegado(
        self,
        delegado: Delegado,
        fecha: date,
        operacion: DelegadoOperacion,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> list:
        """
        Returns a list of tuples (LiquidacionGeneral, EspecialidadRevision, tipo_delegado, DelegadoOperacion) 
        representing candidate liquidaciones for the given pre-resolved DelegadoOperacion.

        A liquidacion is a candidate if:
        1. It belongs to the operacion's municipalidad.
        2. If operacion.tipo_liquidacion_id is set, matches that specific tipo_liquidacion.
           If operacion.tipo_liquidacion_id is None (wildcard), matches any tipo_liquidacion.
        3. The liquidacion requires the operacion's especialidad (in LiquidacionEspecialidadDisponibles).
        4. The liquidacion does NOT already have a LiquidacionDelegado for that especialidad.

        Args:
            delegado: The Delegado ORM object.
            fecha: Reference date for vigencia checks.
            operacion: The pre-resolved DelegadoOperacion (from resolve_delegado_operacion).
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            List of tuples: (LiquidacionGeneral, EspecialidadRevision, tipo_delegado, DelegadoOperacion).
        """
        # Build the base filter for municipalidad
        q_filter = Q(municipalidad_id=operacion.municipalidad_id)

        # If operacion has a specific tipo_liquidacion, match it exactly.
        # If None (wildcard), accept any tipo_liquidacion.
        if operacion.tipo_liquidacion_id:
            q_filter &= Q(tipo_liquidacion_id=operacion.tipo_liquidacion_id)
        # If wildcard (None), we don't add a tipo filter — all tipos accepted

        # The candidate's tipo_liquidacion must have the operation's especialidad available and vigente
        especialidad_valida_para_tipo = LiquidacionEspecialidadDisponibles.objects.filter(
            tipo_liquidacion_id=OuterRef('tipo_liquidacion_id'),
            especialidad_id=operacion.especialidad_revision_id,
            activo=True,
            periodo_inicio__lte=fecha,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
        )

        # The liquidacion must actually have a detail for this especialidad
        # (not just be of a tipo that supports it)
        tiene_detalle_de_especialidad = Exists(
            LiquidacionPorcentajeObraDetalle.objects.filter(
                liquidacion_porcentaje__liquidacion_general_id=OuterRef("pk"),
                especialidad_id=operacion.especialidad_revision_id,
            )
        )

        # The liquidacion must not already be assigned to this delegado in this especialidad
        ya_asignada = LiquidacionDelegado.objects.filter(
            liquidacion_id=OuterRef("pk"),
            especialidad_revision_id=operacion.especialidad_revision_id
        )

        qs = LiquidacionGeneral.objects.filter(q_filter).annotate(
            ya_asignada=Exists(ya_asignada),
            especialidad_valida=Exists(especialidad_valida_para_tipo),
            tiene_el_detalle=tiene_detalle_de_especialidad,
        ).filter(
            ya_asignada=False,
            especialidad_valida=True,
            tiene_el_detalle=True,
        ).select_related(
            "tipo_liquidacion",
            "municipalidad",
            "proyecto",
        ).prefetch_related(
            "comprobantes",
        )

        # Apply date range filter on LiquidacionGeneral.fecha_registro
        if fecha_inicio:
            qs = qs.filter(fecha_registro__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_registro__date__lte=fecha_fin)

        # Build result tuples: (liquidacion, especialidad_revision, tipo_delegado, operacion)
        return [
            (liq, operacion.especialidad_revision, operacion.tipo, operacion)
            for liq in qs
        ]
