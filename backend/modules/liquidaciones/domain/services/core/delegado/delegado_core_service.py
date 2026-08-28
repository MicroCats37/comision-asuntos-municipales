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

    def get_candidatas_for_delegado(
        self,
        delegado: Delegado,
        fecha: date,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> list:
        """
        Returns a list of tuples (LiquidacionGeneral, EspecialidadRevision) representing
        candidate liquidaciones for the given delegado.
        A liquidacion is a candidate if:
        1. It belongs to a municipalidad where the delegado is TITULAR (and matches the tipo).
        2. The liquidacion requires the TITULAR operation's especialidad (in especialidades_revisadas).
        3. The liquidacion does NOT already have a LiquidacionDelegado for that especialidad.

        Args:
            delegado: The Delegado ORM object.
            fecha: Reference date for vigencia checks.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).
        """
        from modules.liquidaciones.domain.constants import TipoDelegado
        
        operaciones_titular = list(
            DelegadoOperacion.objects.filter(
                delegado=delegado,
                tipo=TipoDelegado.TITULAR,
            ).filter(
                Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__isnull=True,
                )
                | Q(
                    periodos__periodo_inicio__lte=fecha,
                    periodos__periodo_fin__gte=fecha,
                )
            ).select_related("especialidad_revision").distinct()
        )
        
        candidatas_tuples = []
        procesadas = set()

        for op in operaciones_titular:
            q_filter = Q(municipalidad_id=op.municipalidad_id)
            if op.liquidacion_revision_id:
                q_filter &= Q(tipo_liquidacion_id=op.liquidacion_revision_id)
            else:
                # liquidacion_revision=None means this operation covers liquidaciones
                # that have NOT yet been assigned a specific tipo_liquidacion revision.
                # Exclude liquidaciones that already have a concrete liquidacion_revision
                # (they belong to other-specific-type operations).
                q_filter &= Q(tipo_liquidacion__isnull=False)

            # The especialidad_valida_para_tipo check only verifies the tipo supports
            # this especialidad — it does NOT verify the liquidacion actually HAS this
            # especialidad in its details. Add a detail-existence filter to ensure
            # only liquidaciones that actually have this especialidad are candidates.
            tiene_detalle_de_especialidad = Exists(
                LiquidacionPorcentajeObraDetalle.objects.filter(
                    liquidacion_porcentaje__liquidacion_general_id=OuterRef("pk"),
                    especialidad_id=op.especialidad_revision_id,
                )
            )

            # Validate via catalog: tipo_liquidacion of the candidate must have
            # op.especialidad_revision_id marked activo=True and vigente on fecha.
            especialidad_valida_para_tipo = LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion_id=OuterRef('tipo_liquidacion_id'),
                especialidad_id=op.especialidad_revision_id,
                activo=True,
                periodo_inicio__lte=fecha,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
            )

            tiene_delegado_en_esta_especialidad = LiquidacionDelegado.objects.filter(
                liquidacion_id=OuterRef("pk"),
                especialidad_revision_id=op.especialidad_revision_id
            )

            qs = LiquidacionGeneral.objects.filter(q_filter).annotate(
                ya_asignada=Exists(tiene_delegado_en_esta_especialidad),
                especialidad_valida=Exists(especialidad_valida_para_tipo),
                tiene_el_detalle=tiene_detalle_de_especialidad,
            ).filter(ya_asignada=False, especialidad_valida=True, tiene_el_detalle=True).select_related(
                "tipo_liquidacion",
                "municipalidad",
                "proyecto",
            )

            # Apply date range filter on LiquidacionGeneral.fecha_registro
            if fecha_inicio:
                qs = qs.filter(fecha_registro__date__gte=fecha_inicio)
            if fecha_fin:
                qs = qs.filter(fecha_registro__date__lte=fecha_fin)
            
            for liq in qs:
                clave = (liq.id, op.especialidad_revision.id)
                if clave not in procesadas:
                    procesadas.add(clave)
                    candidatas_tuples.append((liq, op.especialidad_revision))
                    
        return candidatas_tuples
