"""Core sync para asociaciones LiquidacionInspector."""

import uuid
from datetime import date
from typing import Optional

from django.db import models

from modules.liquidaciones.domain.constants import DelegadoStatus, TipoLiquidacion
from modules.liquidaciones.models import Inspector, LiquidacionGeneral, LiquidacionInspector


class LiquidacionInspectorCore:
    def _obtener_liquidacion_por_id(self, liquidacion_id: uuid.UUID) -> Optional[LiquidacionGeneral]:
        try:
            return LiquidacionGeneral.objects.prefetch_related("liquidaciones_previas").get(id=liquidacion_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

    def _obtener_tipo_previa_io(self, liquidacion: LiquidacionGeneral) -> Optional[str]:
        if liquidacion.tipo_liquidacion != TipoLiquidacion.INSPECCION_OBRA:
            return liquidacion.tipo_liquidacion
        previa = liquidacion.liquidaciones_previas.filter(
            tipo_liquidacion__in=[TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA]
        ).order_by("-created_at").first()
        return previa.tipo_liquidacion if previa else None

    def _obtener_inspector_por_id(self, inspector_id: uuid.UUID) -> Optional[Inspector]:
        try:
            return Inspector.objects.select_related("perfil_ingeniero", "especialidad").get(id=inspector_id)
        except Inspector.DoesNotExist:
            return None

    def _obtener_asociacion(self, liquidacion_id: uuid.UUID, inspector_id: uuid.UUID) -> Optional[LiquidacionInspector]:
        return LiquidacionInspector.objects.filter(
            liquidacion_id=liquidacion_id,
            inspector_id=inspector_id,
        ).select_related(
            "inspector",
            "inspector__perfil_ingeniero",
            "inspector__especialidad",
        ).first()

    def _existe_asociacion(self, liquidacion_id: uuid.UUID, inspector_id: uuid.UUID) -> bool:
        return LiquidacionInspector.objects.filter(
            liquidacion_id=liquidacion_id,
            inspector_id=inspector_id,
        ).exists()

    def _crear_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        inspector_id: uuid.UUID,
        periodo: Optional[str] = None,
        dictamen_revision: Optional[str] = None,
        fecha_presentacion: Optional[date] = None,
        fecha_revision: Optional[date] = None,
    ) -> LiquidacionInspector:
        return LiquidacionInspector.objects.create(
            liquidacion_id=liquidacion_id,
            inspector_id=inspector_id,
            periodo=periodo,
            dictamen_revision=dictamen_revision,
            fecha_presentacion=fecha_presentacion,
            fecha_revision=fecha_revision,
        )

    def _actualizar_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        inspector_id: uuid.UUID,
        periodo: Optional[str] = None,
        dictamen_revision: Optional[str] = None,
        fecha_presentacion: Optional[date] = None,
        fecha_revision: Optional[date] = None,
    ) -> Optional[LiquidacionInspector]:
        try:
            asociacion = LiquidacionInspector.objects.get(liquidacion_id=liquidacion_id, inspector_id=inspector_id)
        except LiquidacionInspector.DoesNotExist:
            return None

        if periodo is not None:
            asociacion.periodo = periodo
        if dictamen_revision is not None:
            asociacion.dictamen_revision = dictamen_revision
        if fecha_presentacion is not None:
            asociacion.fecha_presentacion = fecha_presentacion
        if fecha_revision is not None:
            asociacion.fecha_revision = fecha_revision
        asociacion.save()
        return asociacion

    def _eliminar_asociacion(self, liquidacion_id: uuid.UUID, inspector_id: uuid.UUID) -> bool:
        deleted_count, _ = LiquidacionInspector.objects.filter(
            liquidacion_id=liquidacion_id,
            inspector_id=inspector_id,
        ).delete()
        return deleted_count > 0

    def _es_inspector_activo(self, inspector_id: uuid.UUID) -> bool:
        return Inspector.objects.filter(id=inspector_id, status=DelegadoStatus.ACTIVO).exists()

    def _inspector_vigente(self, inspector_id: uuid.UUID, fecha_referencia: Optional[date] = None) -> bool:
        if fecha_referencia is None:
            from django.utils import timezone
            fecha_referencia = timezone.now().date()
        return Inspector.objects.filter(id=inspector_id, vigencia__gte=fecha_referencia).exists()

    def _tipo_inspector_compatible(self, inspector_id: uuid.UUID, tipo_liquidacion_previa: str) -> bool:
        return Inspector.objects.filter(id=inspector_id, tipo_liquidacion=tipo_liquidacion_previa).exists()

    def _obtener_inspectores_vigentes_por_liquidacion_previa(self, liquidacion_previa_id: uuid.UUID) -> list:
        """
        Obtiene inspectores vigentes y elegibles para una liquidacion previa de IO.

        Deriva el tipo de liquidacion (EDIFICACION o HABILITACION_URBANA) de la
        liquidacion previa y retorna solo inspectores con tipo_liquidacion compatible,
        activos y vigentes.

        Args:
            liquidacion_previa_id: UUID de la liquidacion previa.

        Returns:
            Lista de InspectorVigenteResult.
        """
        from modules.liquidaciones.domain.schemas import InspectorVigenteResult, EspecialidadBasicaResult
        from modules.liquidaciones.models import LiquidacionGeneral
        from django.utils import timezone

        fecha = timezone.now().date()

        try:
            liquidacion_previa = LiquidacionGeneral.objects.filter(id=liquidacion_previa_id).first()
        except Exception:
            return []

        if not liquidacion_previa:
            return []

        tipo_liquidacion = liquidacion_previa.tipo_liquidacion
        if tipo_liquidacion not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            return []

        queryset = Inspector.objects.select_related("perfil_ingeniero", "especialidad").filter(
            status=DelegadoStatus.ACTIVO,
            vigencia__gte=fecha,
            tipo_liquidacion=tipo_liquidacion,
        )

        items = []
        for inspector in queryset:
            perfil = inspector.perfil_ingeniero
            especialidad = inspector.especialidad
            items.append(InspectorVigenteResult(
                id=inspector.id,
                nombre_completo=perfil.nombre_completo if perfil else "",
                cip=perfil.cip if perfil else "",
                especialidad=EspecialidadBasicaResult(id=especialidad.id, nombre=especialidad.nombre) if especialidad else None,
                tipo_liquidacion=inspector.tipo_liquidacion,
                categoria=inspector.categoria,
                numero_registro=inspector.numero_registro,
                vigencia=inspector.vigencia,
            ))
        return items

    def _obtener_inspectores_vigentes(self, liquidacion_id: uuid.UUID, fecha: date) -> list:
        from modules.liquidaciones.domain.schemas import InspectorVigenteResult, EspecialidadBasicaResult

        liquidacion = self._obtener_liquidacion_por_id(liquidacion_id)
        if not liquidacion:
            return []

        tipo_previa = self._obtener_tipo_previa_io(liquidacion)
        if tipo_previa not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            return []

        queryset = Inspector.objects.select_related("perfil_ingeniero", "especialidad").filter(
            status=DelegadoStatus.ACTIVO,
            vigencia__gte=fecha,
            tipo_liquidacion=tipo_previa,
        ).filter(
            ~models.Exists(
                LiquidacionInspector.objects.filter(
                    liquidacion_id=liquidacion_id,
                    inspector_id=models.OuterRef("pk"),
                )
            )
        )

        items = []
        for inspector in queryset:
            perfil = inspector.perfil_ingeniero
            especialidad = inspector.especialidad
            items.append(InspectorVigenteResult(
                id=inspector.id,
                nombre_completo=perfil.nombre_completo if perfil else "",
                cip=perfil.cip if perfil else "",
                especialidad=EspecialidadBasicaResult(id=especialidad.id, nombre=especialidad.nombre) if especialidad else None,
                tipo_liquidacion=inspector.tipo_liquidacion,
                categoria=inspector.categoria,
                numero_registro=inspector.numero_registro,
                vigencia=inspector.vigencia,
            ))
        return items

    def _obtener_inspectores_vigentes_por_tipo(self, tipo_liquidacion: str, fecha: date) -> list:
        """Obtiene inspectores vigentes para un tipo de liquidacion (sin exclusions por liquidacion)."""
        from modules.liquidaciones.domain.schemas import InspectorVigenteResult, EspecialidadBasicaResult

        queryset = Inspector.objects.select_related("perfil_ingeniero", "especialidad").filter(
            status=DelegadoStatus.ACTIVO,
            vigencia__gte=fecha,
            tipo_liquidacion=tipo_liquidacion,
        )

        items = []
        for inspector in queryset:
            perfil = inspector.perfil_ingeniero
            especialidad = inspector.especialidad
            items.append(InspectorVigenteResult(
                id=inspector.id,
                nombre_completo=perfil.nombre_completo if perfil else "",
                cip=perfil.cip if perfil else "",
                especialidad=EspecialidadBasicaResult(id=especialidad.id, nombre=especialidad.nombre) if especialidad else None,
                tipo_liquidacion=inspector.tipo_liquidacion,
                categoria=inspector.categoria,
                numero_registro=inspector.numero_registro,
                vigencia=inspector.vigencia,
            ))
        return items


liquidacion_inspector_core = LiquidacionInspectorCore()
