"""
DelegadoCoreService — operaciones ORM puras para Delegado.

SIN lógica de negocio. Solo: listar, obtener, filtrar.
"""
from datetime import date
from typing import Optional
import uuid
from django.db.models import Q, Exists, OuterRef

from core.exceptions import ConflictError
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
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
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
# Modelos del módulo finanzas que referencian la asignación (LiquidacionDelegado).
# El import es de solo modelos: no genera ciclo con modules.finanzas.domain.services.
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario import (
    ReciboHonorarioDelegado,
)


class DelegadoCoreService:
    """
    Servicio core síncrono para operaciones ORM de Delegado.
    ORM puro — sin lógica de negocio.
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
        Retorna queryset de Delegado paginado con filtros opcionales.
        Usa select_related/prefetch_related para evitar N+1.
        Retorna (queryset, total_count).
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
        Retorna un solo Delegado por UUID.
        Retorna None si no se encuentra.
        """
        return Delegado.objects.select_related(
            'perfil_ingeniero',
        ).filter(id=delegado_id).first()

    def get_delegado_operacion_by_id(
        self,
        operacion_id: uuid.UUID,
    ) -> Optional[DelegadoOperacion]:
        """
        Retorna una sola DelegadoOperacion por UUID con relaciones prefetched.
        Retorna None si no se encuentra.
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
        Retorna todos los registros de DelegadoOperacion para un delegado,
        con su periodo vigente actual.
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
        """Verifica si un periodo está vigente (activo en la fecha dada)."""
        return periodo.periodo_inicio <= today and (
            periodo.periodo_fin is None or periodo.periodo_fin >= today
        )

    def _get_current_periodo(
        self, municipalidad: DelegadoOperacion, today: date
    ) -> Optional[DelegadoOperacionPeriodo]:
        """Retorna el periodo vigente actual para una DelegadoOperacion, o None."""
        periodos = list(municipalidad.periodos.all())
        for periodo in periodos:
            if self._is_vigente(periodo, today):
                return periodo
        return None

    def build_municipalidad_asignada_result(
        self, dm: DelegadoOperacion, today: date
    ) -> MunicipalidadesAsignadasResult:
        """
        Construye MunicipalidadesAsignadasResult a partir de un objeto ORM DelegadoOperacion.
        Encapsula la iteración sobre dm.periodos.all() para encontrar el periodo actual.
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
        Construye DelegadoForMunicipalidadResult a partir de un objeto ORM DelegadoOperacion.
        Encapsula la iteración sobre dm.periodos.all() para encontrar el periodo actual.
        """
        from modules.liquidaciones.domain.results.delegado.delegado_result import PerfilIngenieroResult
        
        current_periodo = self._get_current_periodo(dm, today)
        
        # Construir resultado perfil_ingeniero
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
        Retorna todos los registros de DelegadoOperacion para una municipalidad.
        Si vigente=True, filtra solo períodos actuales (periodo_inicio <= today AND
        (periodo_fin IS NULL OR periodo_fin >= today)).
        Retorna (list[DelegadoOperacion], total).
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
            # Normalizar string→bool desde query params
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
        Retorna una sola LiquidacionGeneral por UUID.
        Retorna None si no se encuentra.
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
        Retorna string especialidad_ids de LiquidacionEspecialidadDisponibles vigentes
        para el tipo_liquidacion con el código dado en la fecha dada.
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
        Retorna candidatos DelegadoOperacion que coinciden con un tipo de liquidación.

        Criterios:
        1. DelegadoOperacion con municipalidad_id AND
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

    def list_delegados_vigentes_por_especialidad(
        self,
        especialidad_revision_id: uuid.UUID,
        fecha: date,
    ) -> list:
        """
        Retorna DelegadoOperacion vigentes filtered by EspecialidadRevision.

        Criterios:
        1. DelegadoOperacion with especialidad_revision_id matching
        2. periodo municipal vigente (inicio <= fecha AND fin IS NULL OR >= fecha)
        """
        return list(
            DelegadoOperacion.objects.filter(
                especialidad_revision_id=especialidad_revision_id,
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

    def list_delegados_vigentes_por_especialidad_delegados(
        self,
        especialidad_revision_id: uuid.UUID,
        fecha: date,
    ) -> list:
        """
        Retorna Delegado entities (unique) that have at least one vigente
        DelegadoOperacion for the given EspecialidadRevision.

        Uses Exists/OuterRef to query the correct root entity (Delegado)
        instead of deduplicating DelegadoOperacion rows.

        Criterios:
        1. Delegado has at least one DelegadoOperacion where
           - operacion.especialidad_revision_id = especialidad_revision_id
           - operacion.delegado_id = Delegado.pk
           - existe un periodo con periodo_inicio <= fecha AND
             (periodo_fin IS NULL OR periodo_fin >= fecha)
        2. Results ordered by perfil_ingeniero.apellido_paterno,
           apellido_materno, nombres
        """
        # Subquery: check if a DelegadoOperacion has a vigente periodo for this
        # especialidad_revision and fecha
        from django.db.models import OuterRef, Exists

        vigencia_subquery = DelegadoOperacionPeriodo.objects.filter(
            delegado_municipalidad=OuterRef("pk"),
            periodo_inicio__lte=fecha,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
        )

        operacion_subquery = DelegadoOperacion.objects.filter(
            delegado_id=OuterRef("pk"),
            especialidad_revision_id=especialidad_revision_id,
        ).filter(
            Q(periodos__periodo_inicio__lte=fecha)
            & (Q(periodos__periodo_fin__isnull=True) | Q(periodos__periodo_fin__gte=fecha))
        )

        return list(
            Delegado.objects.filter(
                Exists(operacion_subquery)
            ).select_related(
                "perfil_ingeniero",
            ).order_by(
                "perfil_ingeniero__apellido_paterno",
                "perfil_ingeniero__apellido_materno",
                "perfil_ingeniero__nombres",
            ).distinct()
        )

    def get_asignacion_municipal_vigente(
        self,
        delegado_id: uuid.UUID,
        municipalidad_id: uuid.UUID,
        fecha: date,
    ) -> Optional[DelegadoOperacion]:
        """
        Retorna la DelegadoOperacion para (delegado, municipalidad) con un
        periodo vigente en la fecha dada, o None.
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
        creado_por_rh: bool = False,
        **kwargs,
    ) -> LiquidacionDelegado:
        """
        Crea una asociación LiquidacionDelegado (wrapper ORM puro).

        Args:
            liquidacion: FK a LiquidacionGeneral.
            delegado: FK a Delegado.
            especialidad_revision: FK a EspecialidadRevision.
            creado_por_rh: Provenance de la asignación. False (default) la
                conserva siempre al eliminar un RH; solo el flujo RH mensual
                crea asignaciones con provenance RH.
        """
        return LiquidacionDelegado.objects.create(
            liquidacion=liquidacion,
            delegado=delegado,
            especialidad_revision=especialidad_revision,
            creado_por_rh=creado_por_rh,
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
        Actualiza campos de metadatos de una asociación LiquidacionDelegado.
        Retorna la instancia actualizada, o None si la asociación no existe.

        La asignación queda PROTEGIDA si tiene algún detalle de honorario
        vinculado a un RH mensual: en ese caso se lanza ConflictError (409)
        ANTES de escribir nada (misma regla de seguridad que la remoción).
        """
        asociacion = (
            LiquidacionDelegado.objects
            .filter(liquidacion=liquidacion, delegado=delegado)
            .select_related("delegado__perfil_ingeniero")
            .first()
        )
        if not asociacion:
            return None
        self._bloquear_edicion_con_rh_mensual(asignacion)
        for campo, valor in campos.items():
            setattr(asociacion, campo, valor)
        asociacion.save()
        return asociacion

    def actualizar_asignacion_por_id(
        self,
        liquidacion,
        liquidacion_delegado_id,
        campos: dict,
    ) -> Optional[LiquidacionDelegado]:
        """
        Actualiza una asociación LiquidacionDelegado identificada por su propio PK.

        A diferencia de `actualizar_liquidacion_delegado` (que resuelve por
        delegado), aquí el objetivo es la fila exacta. La pertenencia a la
        liquidación se filtra en la query, de modo que una asignación de otra
        liquidación nunca se toca.

        Retorna la instancia actualizada, o None si la asignación no existe o no
        pertenece a la liquidación.

        La asignación queda PROTEGIDA si tiene algún detalle de honorario
        vinculado a un RH mensual: en ese caso se lanza ConflictError (409)
        ANTES de escribir nada (misma regla de seguridad que la remoción).
        """
        asignacion = (
            LiquidacionDelegado.objects
            .filter(
                id=liquidacion_delegado_id,
                liquidacion_id=liquidacion.id,
            )
            .select_related(
                "liquidacion",
                "delegado__perfil_ingeniero",
                "especialidad_revision",
            )
            .first()
        )
        if not asignacion:
            return None
        self._bloquear_edicion_con_rh_mensual(asignacion)
        for campo, valor in campos.items():
            setattr(asignacion, campo, valor)
        asignacion.save()
        return asignacion

    def _bloquear_edicion_con_rh_mensual(self, asignacion) -> None:
        """
        Lanza ConflictError (409) si la asignación está protegida por un RH mensual.

        Espejo de la regla 1 de `eliminar_asignacion_con_guardas_rh`: si algún
        DetalleHonorarioDelegado de la asignación está vinculado a un
        ReciboHonorarioDelegadoMensual, sus importes están congelados y son
        propiedad del flujo RH, así que la metadata de la asignación NO es
        editable a mano.

        Se evalúa ANTES de cualquier escritura: cuando la guarda salta no se
        escribe la asignación, ni el detalle, ni el RH mensual, ni la
        liquidación.

        Args:
            asignacion: LiquidacionDelegado objetivo de la edición.

        Raises:
            ConflictError: 409 si un RH mensual protege la asignación.
        """
        tiene_rh_mensual = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado_id=asignacion.id,
            recibo_mensual__isnull=False,
        ).exists()
        if not tiene_rh_mensual:
            return
        label = self._get_delegado_label(asignacion.delegado)
        raise ConflictError(
            f"No se puede editar la asignación del delegado '{label}' porque "
            "tiene detalles de honorario vinculados a un recibo de honorario "
            "mensual. Elimina primero el recibo mensual."
        )

    def eliminar_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
    ) -> tuple:
        """
        Elimina la asociación LiquidacionDelegado para (liquidacion, delegado).

        Atajo de `eliminar_asignacion_con_guardas_rh`: la eliminación de una
        asignación SIEMPRE está guardada por sus referencias financieras.
        """
        return self.eliminar_asignacion_con_guardas_rh(
            liquidacion=liquidacion,
            delegado=delegado,
        )

    def eliminar_asignacion_con_guardas_rh(
        self,
        liquidacion,
        delegado,
    ) -> tuple:
        """
        Elimina las asignaciones (LiquidacionDelegado) de (liquidacion, delegado)
        evaluando antes las referencias financieras que las protegen.

        La decisión se basa en el ESTADO DE REFERENCIA de las asignaciones, no
        en la procedencia RH (`creado_por_rh`): una asignación creada por el
        flujo RH y una manual o heredada se evalúan igual.

        1. Si algún DetalleHonorarioDelegado tiene `recibo_mensual` → 409.
           Ese detalle pertenece a un RH mensual con totales congelados:
           borrarlo desincronizaría el RH.
        2. Si existe un ReciboHonorarioDelegado (recibo no mensual) → 409.
        3. Sin bloqueos: se eliminan primero los detalles huérfanos
           (`recibo_mensual IS NULL`) y después TODAS las asignaciones del
           delegado en la liquidación (una por especialidad de revisión).

        Nunca elimina la LiquidacionGeneral ni ningún ReciboHonorarioDelegadoMensual,
        y nunca recalcula totales de RH.

        Args:
            liquidacion: FK a LiquidacionGeneral.
            delegado: FK a Delegado.

        Returns:
            Tupla (total_eliminado, detalle_por_modelo) de Django.

        Raises:
            ConflictError: 409 si una referencia financiera bloquea la eliminación.
        """
        asignacion_ids = list(
            LiquidacionDelegado.objects.filter(
                liquidacion=liquidacion, delegado=delegado,
            ).values_list("id", flat=True)
        )
        if not asignacion_ids:
            return 0, {}

        label = self._get_delegado_label(delegado)

        tiene_detalle_rh_mensual = (
            DetalleHonorarioDelegado.objects.filter(
                liquidacion_delegado_id__in=asignacion_ids,
                recibo_mensual__isnull=False,
            ).exists()
        )
        if tiene_detalle_rh_mensual:
            raise ConflictError(
                f"No se puede quitar el delegado '{label}' porque tiene detalles "
                "de honorario vinculados a un recibo de honorario mensual. "
                "Elimina primero el recibo mensual."
            )

        tiene_recibo_honorario = (
            ReciboHonorarioDelegado.objects.filter(
                liquidacion_delegado_id__in=asignacion_ids,
            ).exists()
        )
        if tiene_recibo_honorario:
            raise ConflictError(
                f"No se puede quitar el delegado '{label}' porque tiene un "
                "recibo de honorario asociado."
            )

        # Detalles huérfanos (sin RH mensual detrás) → se eliminan primero:
        # la asignación está en PROTECT y no se puede borrar antes.
        DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado_id__in=asignacion_ids,
            recibo_mensual__isnull=True,
        ).delete()

        # Asignaciones: todas las especialidades de revisión de este delegado.
        return LiquidacionDelegado.objects.filter(
            id__in=asignacion_ids,
        ).delete()

    @staticmethod
    def _get_delegado_label(delegado) -> str:
        """
        Etiqueta legible de un delegado para los mensajes de error.

        Usa el CIP o el nombre completo; nunca el UUID crudo (los mensajes de
        error no deben filtrar identificadores internos).
        """
        perfil = getattr(delegado, "perfil_ingeniero", None)
        cip = getattr(perfil, "cip", None) if perfil is not None else None
        nombre = getattr(perfil, "nombre_completo", None) if perfil is not None else None
        return cip or nombre or str(delegado)

    def obtener_liquidacion_delegado(
        self,
        liquidacion,
        delegado,
    ) -> Optional[LiquidacionDelegado]:
        """
        Retorna la asociación LiquidacionDelegado para (liquidacion, delegado),
        o None.
        """
        return LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion, delegado=delegado,
        ).select_related(
            "delegado__perfil_ingeniero",
            "especialidad_revision",
        ).first()

    # ── Alcance RH: provenance y verificación de referencias ─────────────────────

    def get_liquidacion_delegado_por_id(
        self,
        liquidacion_delegado_id,
    ) -> Optional[LiquidacionDelegado]:
        """
        Retorna la asignación (LiquidacionDelegado) por su PK, o None.
        """
        return (
            LiquidacionDelegado.objects
            .filter(id=liquidacion_delegado_id)
            .select_related(
                "liquidacion",
                "delegado__perfil_ingeniero",
                "delegado_operacion",
                "especialidad_revision",
            )
            .first()
        )

    def list_liquidaciones_delegadas_por_ids(
        self,
        liquidacion_delegado_ids,
    ) -> list[LiquidacionDelegado]:
        """
        Retorna las asignaciones (LiquidacionDelegado) de una lista de PK.

        Los PK inexistentes se omiten del resultado.
        """
        ids = [i for i in dict.fromkeys(liquidacion_delegado_ids) if i is not None]
        if not ids:
            return []
        return list(
            LiquidacionDelegado.objects
            .filter(id__in=ids)
            .select_related(
                "liquidacion",
                "delegado__perfil_ingeniero",
                "delegado_operacion",
                "especialidad_revision",
            )
        )

    def tiene_proveniencia_rh(
        self,
        liquidacion_delegado_id,
    ) -> bool:
        """
        Indica si la asignación fue creada por el flujo RH mensual.

        Las asignaciones históricas o manuales NO tienen provenance RH — en ese
        caso la asignación se conserva siempre.
        """
        return LiquidacionDelegado.objects.filter(
            id=liquidacion_delegado_id,
            creado_por_rh=True,
        ).exists()

    def contar_referencias_asignacion(
        self,
        liquidacion_delegado_id,
        exclude_recibo_mensual_id=None,
    ) -> int:
        """
        Cuenta las referencias vivas a una asignación (LiquidacionDelegado).

        Considera:
        - DetalleHonorarioDelegado (detalle de RH mensual) — FK con PROTECT.
        - ReciboHonorarioDelegado (recibo de honorario) — FK con PROTECT.

        Args:
            liquidacion_delegado_id: PK de la asignación.
            exclude_recibo_mensual_id: Opcional — excluye los detalles que
                pertenecen a ese RH mensual (ya retirado).

        Returns:
            Número de referencias vivas.
        """
        detalles_qs = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado_id=liquidacion_delegado_id,
        )
        if exclude_recibo_mensual_id is not None:
            detalles_qs = detalles_qs.exclude(
                recibo_mensual_id=exclude_recibo_mensual_id,
            )
        return (
            detalles_qs.count()
            + ReciboHonorarioDelegado.objects.filter(
                liquidacion_delegado_id=liquidacion_delegado_id,
            ).count()
        )

    def eliminar_asignacion_creada_por_rh(
        self,
        liquidacion_delegado_id,
    ) -> bool:
        """
        Elimina la asignación SOLO si tiene provenance RH (creado_por_rh=True).

        No modifica ningún metadato compartido (número de RH, periodo, mes,
        dictamen ni fechas) y nunca toca Delegado ni DelegadoOperacion.

        Returns:
            True si la asignación fue eliminada, False si se retiene.
        """
        eliminada, _ = LiquidacionDelegado.objects.filter(
            id=liquidacion_delegado_id,
            creado_por_rh=True,
        ).delete()
        return eliminada > 0

    def limpiar_asignaciones_por_rh(
        self,
        liquidacion_delegado_ids,
        exclude_recibo_mensual_id=None,
    ) -> dict[str, list[str]]:
        """
        Limpieza acotada de asignaciones tras retirar los detalles de un RH.

        Una asignación se elimina únicamente cuando:
        1. tiene provenance RH (fue creada por el flujo RH), y
        2. no está referenciada por ningún otro detalle ni recibo.

        Las asignaciones compartidas o históricas se conservan intactas.

        Args:
            liquidacion_delegado_ids: PKs de las asignaciones a evaluar.
            exclude_recibo_mensual_id: Opcional — excluye los detalles que
                pertenecen a ese RH mensual.

        Returns:
            Dict con las listas de ids eliminadas y retenidas.
        """
        eliminadas: list[str] = []
        retenidas: list[str] = []

        for asignacion_id in dict.fromkeys(liquidacion_delegado_ids):
            if asignacion_id is None:
                continue

            if not self.tiene_proveniencia_rh(asignacion_id):
                # Asignación histórica o manual — se conserva siempre.
                retenidas.append(str(asignacion_id))
                continue

            referencias = self.contar_referencias_asignacion(
                asignacion_id,
                exclude_recibo_mensual_id=exclude_recibo_mensual_id,
            )
            if referencias > 0:
                # Asignación compartida con otro RH o recibo — se conserva.
                retenidas.append(str(asignacion_id))
                continue

            if self.eliminar_asignacion_creada_por_rh(asignacion_id):
                eliminadas.append(str(asignacion_id))
            else:
                retenidas.append(str(asignacion_id))

        return {"eliminadas": eliminadas, "retenidas": retenidas}

    def list_liquidacion_delegado_paginated(
        self,
        page: int,
        page_size: int,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Retorna queryset paginado de LiquidacionDelegado con filtros opcionales.
        Usa select_related para evitar N+1: liquidacion, liquidacion__proyecto,
        liquidacion__municipalidad, liquidacion__tipo_liquidacion, delegado,
        delegado__perfil_ingeniero, especialidad_revision.
        Retorna (queryset_list, total_count).
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

    def list_asignaciones_con_detalle_rh(
        self,
        liquidacion_id: uuid.UUID,
    ) -> list[LiquidacionDelegado]:
        """
        Retorna las asignaciones (LiquidacionDelegado) de una liquidación con su
        detalle RH y su RH mensual precargados.

        Presupuesto FIJO de 3 queries (sin N+1, sin count() — no hay paginación):
          1. Asignaciones + delegado.perfil_ingeniero + especialidad_revision
             + delegado_operacion (LEFT JOIN: la FK es nullable).
          2. Detalles de honorario (DetalleHonorarioDelegado) de esas asignaciones.
          3. Recibos RH mensuales (ReciboHonorarioDelegadoMensual) de esos detalles.

        El orden es estable: apellido paterno, apellido materno y especialidad
        de revisión.

        Nota: NO se accede a `ld.recibo_honorario` (OneToOneField) — su accessor
        inverso lanza RelatedObjectDoesNotExist cuando no existe. El RH mensual
        se cuelga del DETALLE (`detalles_honorario__recibo_mensual`), no de la
        asignación.
        """
        return list(
            LiquidacionDelegado.objects.filter(
                liquidacion_id=liquidacion_id,
            ).select_related(
                "delegado__perfil_ingeniero",
                "especialidad_revision",
                "delegado_operacion",
            ).prefetch_related(
                "detalles_honorario__recibo_mensual",
            ).order_by(
                "delegado__perfil_ingeniero__apellido_paterno",
                "delegado__perfil_ingeniero__apellido_materno",
                "especialidad_revision__nombre",
            )
        )

    def resolve_delegado_operacion(
        self,
        delegado: Delegado,
        municipalidad_id: uuid.UUID,
        tipo_liquidacion_id: uuid.UUID,
        tipo_delegado: str,
        fecha: date,
    ) -> Optional[DelegadoOperacion]:
        """
        Resuelve exactamenta UNA DelegadoOperacion activa que coincide con:
          cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + vigencia actual.

        Lógica de resolución:
        1. Busca todas las operaciones activas para (delegado, municipalidad, tipo_delegado) con periodo vigente.
        2. Entre ellas, coincide en tipo_liquidacion:
           - Si una operación tiene tipo_liquidacion_id coincidente exactamente -> usarla.
           - Si una operación tiene tipo_liquidacion_id=None (wildcard) -> es candidato.
        3. Si existen coincidencia exacta Y wildcard -> 409 conflicto (ambigüedad).
        4. Si solo hay wildcard -> usar el wildcard.
        5. Si solo hay exacta -> usar la exacta.
        6. Si ninguna coincide -> 404.

        Retorna:
            La DelegadoOperacion resuelta.

        Lanza:
            HttpError 404: No se encontró operación coincidente.
            HttpError 409: Coincidencia ambigua (existe wildcard y exacta).
        """
        from ninja.errors import HttpError
        from modules.liquidaciones.domain.constants import TipoDelegado

        # Obtener todas las operaciones activas para este delegado/municipalidad/tipo con periodo vigente
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

        # Separar en coincidencia exacta (tipo_liquidacion == tipo_liquidacion_id) y wildcard (null)
        exact_matches = [op for op in active_ops if op.tipo_liquidacion_id == tipo_liquidacion_id]
        wildcard_matches = [op for op in active_ops if op.tipo_liquidacion_id is None]

        # Caso: existen exacta y wildcard -> ambigüedad -> 409
        if exact_matches and wildcard_matches:
            raise HttpError(409, "Configuración ambigua: existe operación wildcard y específica para este tipo de liquidación")

        # Caso: existe coincidencia exacta
        if exact_matches:
            if len(exact_matches) > 1:
                raise HttpError(409, "Múltiples operaciones activas coinciden con los criterios")
            return exact_matches[0]

        # Caso: existe coincidencia wildcard
        if wildcard_matches:
            if len(wildcard_matches) > 1:
                raise HttpError(409, "Múltiples operaciones wildcard coinciden con los criterios")
            return wildcard_matches[0]

        # Caso: no se encontró coincidencia
        raise HttpError(404, "No se encontró operación activa para los criterios dados")

    def get_operatividades_delegado(
        self,
        delegado: Delegado,
        fecha: date,
        vigente: Optional[bool] = None,
    ) -> list:
        """
        Retorna los registros de DelegadoOperacion para un delegado, filtrados
        opcionalmente por su vigencia en la fecha dada.

        Args:
            delegado: El objeto ORM Delegado.
            fecha: Fecha de referencia para verificación de vigencia.

        Returns:
            Lista de objetos ORM DelegadoOperacion con relaciones prefetched.
        """
        qs = DelegadoOperacion.objects.filter(delegado=delegado)
        periodo_vigente = Q(
            periodos__periodo_inicio__lte=fecha,
            periodos__periodo_fin__isnull=True,
        ) | Q(
            periodos__periodo_inicio__lte=fecha,
            periodos__periodo_fin__gte=fecha,
        )
        if vigente is True:
            qs = qs.filter(periodo_vigente)
        elif vigente is False:
            qs = qs.exclude(periodo_vigente)

        return list(
            qs.select_related(
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
        Retorna una lista de tuplas (LiquidacionGeneral, EspecialidadRevision, tipo_delegado, DelegadoOperacion)
        representando liquidaciones candidatas para la DelegadoOperacion pre-resuelta dada.

        Una liquidacion es candidata si:
        1. Pertenece a la municipalidad de la operación.
        2. Si operacion.tipo_liquidacion_id está configurado, coincide con ese tipo_liquidacion específico.
           Si operacion.tipo_liquidacion_id es None (wildcard), coincide con cualquier tipo_liquidacion.
        3. La liquidacion requiere la especialidad de la operación (en LiquidacionEspecialidadDisponibles).
        4. La liquidacion NO tiene ya un LiquidacionDelegado para esa especialidad.

        Args:
            delegado: El objeto ORM Delegado.
            fecha: Fecha de referencia para verificación de vigencia.
            operacion: La DelegadoOperacion pre-resuelta (de resolve_delegado_operacion).
            fecha_inicio: Filtro opcional — fecha_registro >= fecha_inicio (inclusivo).
            fecha_fin: Filtro opcional — fecha_registro <= fecha_fin (inclusivo).

        Returns:
            Lista de tuplas: (LiquidacionGeneral, EspecialidadRevision, tipo_delegado, DelegadoOperacion).
        """
        # Construir el filtro base para municipalidad
        q_filter = Q(municipalidad_id=operacion.municipalidad_id)

        # Si operacion tiene un tipo_liquidacion específico, coincidencia exacta.
        # Si es None (wildcard), aceptar cualquier tipo_liquidacion.
        if operacion.tipo_liquidacion_id:
            q_filter &= Q(tipo_liquidacion_id=operacion.tipo_liquidacion_id)
        # Si es wildcard (None), no se añade filtro de tipo — se aceptan todos

        # El tipo_liquidacion del candidato debe tener la especialidad de la operación disponible y vigente
        especialidad_valida_para_tipo = LiquidacionEspecialidadDisponibles.objects.filter(
            tipo_liquidacion_id=OuterRef('tipo_liquidacion_id'),
            especialidad_id=operacion.especialidad_revision_id,
            activo=True,
            periodo_inicio__lte=fecha,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
        )

        # La liquidacion debe tener efectivamente un detalle para esta especialidad
        # (no solo ser de un tipo que la soporta)
        tiene_detalle_de_especialidad = Exists(
            LiquidacionPorcentajeObraDetalle.objects.filter(
                liquidacion_porcentaje__liquidacion_general_id=OuterRef("pk"),
                especialidad_id=operacion.especialidad_revision_id,
            )
        )

        # La liquidacion no debe estar ya asignada a este delegado en esta especialidad
        ya_asignada = LiquidacionDelegado.objects.filter(
            liquidacion_id=OuterRef("pk"),
            especialidad_revision_id=operacion.especialidad_revision_id
        )

        qs = LiquidacionGeneral.objects.filter(q_filter).annotate(
            ya_asignada=Exists(ya_asignada),
            especialidad_valida=Exists(especialidad_valida_para_tipo),
            tiene_el_detalle=Exists(tiene_detalle_de_especialidad),
        ).filter(
            ya_asignada=False,
            especialidad_valida=True,
        )

        # Apply tiene_el_detalle=True only for PO types (EDIFICACION, IMPACTO_VIAL, TALUDES).
        # M2 types (HABILITACION_URBANA, MECANICA_SUELOS) and wildcard operations
        # do not require LiquidacionPorcentajeObraDetalle and must not be excluded.
        from modules.liquidaciones.domain.constants import PO_TIPOS_CON_DETALLE
        tipo_codigo = operacion.tipo_liquidacion.codigo if operacion.tipo_liquidacion else None
        if tipo_codigo in PO_TIPOS_CON_DETALLE:
            qs = qs.filter(tiene_el_detalle=True)

        qs = qs.select_related(
            "tipo_liquidacion",
            "municipalidad",
            "proyecto",
        ).prefetch_related(
            "comprobantes",
        )

        # Aplicar filtro de rango de fechas en LiquidacionGeneral.fecha_registro
        if fecha_inicio:
            qs = qs.filter(fecha_registro__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_registro__date__lte=fecha_fin)

        # Construir tuplas de resultado: (liquidacion, especialidad_revision, tipo_delegado, operacion)
        return [
            (liq, operacion.especialidad_revision, operacion.tipo, operacion)
            for liq in qs
        ]

    def get_candidatas_for_delegado_paginated(
        self,
        delegado: Delegado,
        fecha: date,
        operacion: DelegadoOperacion,
        page: int,
        page_size: int,
        expediente: str | None = None,
        numero: int | None = None,
        propietario: str | None = None,
        direccion: str | None = None,
        comprobante_serie: str | None = None,
        comprobante_numero: str | None = None,
        documento: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> tuple:
        """
        Retorna paginated candidatas para la DelegadoOperacion pre-resuelta dada.

        Filtros adicionales:
        - expediente: icontains sobre LiquidacionGeneral.expediente
        - numero: exact match sobre el numero de la liquidacion específica (edificaciones__numero,
          habilitacion_urbana__numero, mecanica_suelos__numero, taludes__numero,
          impacto_vial__numero, inspeccion_obra__numero)
        - propietario: icontains sobre LiquidacionGeneral.proyecto.nombre_propietario
        - direccion: icontains sobre LiquidacionGeneral.proyecto.direccion

        Returns:
            Tuple of (list of tuples, total count).
        """
        # Construir el filtro base para municipalidad
        q_filter = Q(municipalidad_id=operacion.municipalidad_id)

        if operacion.tipo_liquidacion_id:
            q_filter &= Q(tipo_liquidacion_id=operacion.tipo_liquidacion_id)

        # El tipo_liquidacion del candidato debe tener la especialidad de la operación disponible y vigente
        especialidad_valida_para_tipo = LiquidacionEspecialidadDisponibles.objects.filter(
            tipo_liquidacion_id=OuterRef('tipo_liquidacion_id'),
            especialidad_id=operacion.especialidad_revision_id,
            activo=True,
            periodo_inicio__lte=fecha,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
        )

        # La liquidacion debe tener efectivamente un detalle para esta especialidad
        tiene_detalle_de_especialidad = Exists(
            LiquidacionPorcentajeObraDetalle.objects.filter(
                liquidacion_porcentaje__liquidacion_general_id=OuterRef("pk"),
                especialidad_id=operacion.especialidad_revision_id,
            )
        )

        # La liquidacion no debe estar ya asignada a este delegado en esta especialidad
        ya_asignada = LiquidacionDelegado.objects.filter(
            liquidacion_id=OuterRef("pk"),
            especialidad_revision_id=operacion.especialidad_revision_id
        )

        qs = LiquidacionGeneral.objects.filter(q_filter).annotate(
            ya_asignada=Exists(ya_asignada),
            especialidad_valida=Exists(especialidad_valida_para_tipo),
            tiene_el_detalle=Exists(tiene_detalle_de_especialidad),
        ).filter(
            ya_asignada=False,
            especialidad_valida=True,
        )

        # Apply tiene_el_detalle=True only for PO types (EDIFICACION, IMPACTO_VIAL, TALUDES).
        # M2 types (HABILITACION_URBANA, MECANICA_SUELOS) and wildcard operations
        # do not require LiquidacionPorcentajeObraDetalle and must not be excluded.
        from modules.liquidaciones.domain.constants import PO_TIPOS_CON_DETALLE
        tipo_codigo = operacion.tipo_liquidacion.codigo if operacion.tipo_liquidacion else None
        if tipo_codigo in PO_TIPOS_CON_DETALLE:
            qs = qs.filter(tiene_el_detalle=True)

        qs = qs.select_related(
            "tipo_liquidacion",
            "municipalidad",
            "proyecto",
        ).prefetch_related(
            "comprobantes",
        )

        # Apply filters
        if expediente:
            qs = qs.filter(expediente__icontains=expediente)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if direccion:
            qs = qs.filter(proyecto__direccion__icontains=direccion)
        if numero is not None:
            qs = qs.filter(
                Q(edificaciones__numero=numero)
                | Q(habilitacion_urbana__numero=numero)
                | Q(mecanica_suelos__numero=numero)
                | Q(taludes__numero=numero)
                | Q(impacto_vial__numero=numero)
                | Q(inspeccion_obra__numero=numero)
            )
        comprobante_activo = LiquidacionComprobante.objects.filter(
            liquidacion_general_id=OuterRef("pk"), activo=True
        )
        if comprobante_serie:
            qs = qs.filter(
                Exists(comprobante_activo.filter(serie__icontains=comprobante_serie))
            )
        if comprobante_numero:
            qs = qs.filter(
                Exists(comprobante_activo.filter(numero__icontains=comprobante_numero))
            )
        if documento:
            qs = qs.filter(
                proyecto__entidad_numero_documento__icontains=documento
            )
        if fecha_inicio:
            qs = qs.filter(fecha_registro__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_registro__date__lte=fecha_fin)

        total = qs.count()
        offset = (page - 1) * page_size
        qs_paginated = qs[offset:offset + page_size]

        return [
            (liq, operacion.especialidad_revision, operacion.tipo, operacion)
            for liq in qs_paginated
        ], total
