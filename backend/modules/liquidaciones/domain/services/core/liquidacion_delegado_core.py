"""
LiquidacionDelegado Core — operaciones sync de ORM para asociaciones.

Provee métodos para crear, obtener, actualizar y eliminar asociaciones
LiquidacionDelegado usando delegado_id como clave dentro de una liquidación.

NO usa transaction.atomic internamente — el flujo lo provee si es necesario.
NO contiene lógica de negocio — solo operaciones de datos.

Patrón de nomenclatura:
    - _obtener_<modelo>: retrieval por ID
    - _crear_<asociacion>: creación de nueva asociación
    - _actualizar_<asociacion>: actualización de campos
    - _eliminar_<asociacion>: eliminación por clave
    - _existe_<asociacion>: verificación de existencia
"""
import uuid
from datetime import date
from typing import Optional

from django.db import models

from modules.liquidaciones.models import (
    LiquidacionDelegado,
    LiquidacionGeneral,
    Delegado,
    MunicipalidadDelegado,
    PeriodoDelegado,
)
from modules.liquidaciones.domain.constants import CategoriaDelegado


class LiquidacionDelegadoCore:
    """
    Servicio core sync para operaciones de LiquidacionDelegado.

    Maneja la tabla intermedia entre LiquidacionGeneral y Delegado.
    """

    # -------------------------------------------------------------------------
    # Getters de Entidades Principales
    # -------------------------------------------------------------------------

    def _obtener_liquidacion_por_id(self, liquidacion_id: uuid.UUID) -> Optional[LiquidacionGeneral]:
        """
        Obtiene una LiquidacionGeneral por ID con relaciones preload.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneral o None si no existe
        """
        try:
            return LiquidacionGeneral.objects.select_related(
                'municipalidad',
            ).get(id=liquidacion_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

    def _obtener_liquidacion_por_public_id(self, public_id: str) -> Optional[LiquidacionGeneral]:
        """
        Obtiene una LiquidacionGeneral por public_id (ej. LIQ-2026-00001).

        Args:
            public_id: ID público de la liquidación

        Returns:
            LiquidacionGeneral o None si no existe
        """
        try:
            return LiquidacionGeneral.objects.select_related(
                'municipalidad',
            ).get(public_id=public_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

    def _obtener_delegado_por_id(self, delegado_id: uuid.UUID) -> Optional[Delegado]:
        """
        Obtiene un Delegado por ID con relaciones preload.

        Args:
            delegado_id: UUID del delegado

        Returns:
            Delegado o None si no existe
        """
        try:
            return Delegado.objects.select_related(
                'perfil_ingeniero',
                'especialidad',
            ).get(id=delegado_id)
        except Delegado.DoesNotExist:
            return None

    # -------------------------------------------------------------------------
    # Getters de Asociación
    # -------------------------------------------------------------------------

    def _obtener_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        delegado_id: uuid.UUID,
    ) -> Optional[LiquidacionDelegado]:
        """
        Obtiene una asociación LiquidacionDelegado por liquidación + delegado.

        Args:
            liquidacion_id: UUID de la liquidación
            delegado_id: UUID del delegado

        Returns:
            LiquidacionDelegado o None si no existe
        """
        return LiquidacionDelegado.objects.filter(
            liquidacion_id=liquidacion_id,
            delegado_id=delegado_id,
        ).select_related(
            'delegado',
            'delegado__perfil_ingeniero',
            'delegado__especialidad',
        ).first()

    def _listar_asociaciones_por_liquidacion(
        self,
        liquidacion_id: uuid.UUID,
    ) -> list[LiquidacionDelegado]:
        """
        Lista todas las asociaciones de una liquidación.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            Lista de LiquidacionDelegado
        """
        return list(
            LiquidacionDelegado.objects.filter(
                liquidacion_id=liquidacion_id,
            ).select_related(
                'delegado',
                'delegado__perfil_ingeniero',
                'delegado__especialidad',
            ).order_by('delegado__perfil_ingeniero__apellido_paterno')
        )

    def _existe_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        delegado_id: uuid.UUID,
    ) -> bool:
        """
        Verifica si existe una asociación LiquidacionDelegado.

        Args:
            liquidacion_id: UUID de la liquidación
            delegado_id: UUID del delegado

        Returns:
            True si existe, False otherwise
        """
        return LiquidacionDelegado.objects.filter(
            liquidacion_id=liquidacion_id,
            delegado_id=delegado_id,
        ).exists()

    # -------------------------------------------------------------------------
    # CRUD de Asociación
    # -------------------------------------------------------------------------

    def _crear_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        delegado_id: uuid.UUID,
        periodo: Optional[str] = None,
        dictamen_revision: Optional[str] = None,
        fecha_presentacion: Optional[date] = None,
        fecha_revision: Optional[date] = None,
    ) -> LiquidacionDelegado:
        """
        Crea una nueva asociación LiquidacionDelegado.

        Args:
            liquidacion_id: UUID de la liquidación
            delegado_id: UUID del delegado
            periodo: Periodo de asignación (opcional)
            dictamen_revision: Dictamen de revisión (opcional)
            fecha_presentacion: Fecha de presentación (opcional)
            fecha_revision: Fecha de revisión (opcional)

        Returns:
            LiquidacionDelegado creada
        """
        return LiquidacionDelegado.objects.create(
            liquidacion_id=liquidacion_id,
            delegado_id=delegado_id,
            periodo=periodo,
            dictamen_revision=dictamen_revision,
            fecha_presentacion=fecha_presentacion,
            fecha_revision=fecha_revision,
        )

    def _actualizar_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        delegado_id: uuid.UUID,
        periodo: Optional[str] = None,
        dictamen_revision: Optional[str] = None,
        fecha_presentacion: Optional[date] = None,
        fecha_revision: Optional[date] = None,
    ) -> Optional[LiquidacionDelegado]:
        """
        Actualiza campos de una asociación LiquidacionDelegado existente.

        Solo actualiza los campos que no son None.

        Args:
            liquidacion_id: UUID de la liquidación
            delegado_id: UUID del delegado
            periodo: Periodo de asignación (opcional)
            dictamen_revision: Dictamen de revisión (opcional)
            fecha_presentacion: Fecha de presentación (opcional)
            fecha_revision: Fecha de revisión (opcional)

        Returns:
            LiquidacionDelegado actualizada o None si no existe
        """
        try:
            asociacion = LiquidacionDelegado.objects.get(
                liquidacion_id=liquidacion_id,
                delegado_id=delegado_id,
            )
        except LiquidacionDelegado.DoesNotExist:
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

    def _eliminar_asociacion(
        self,
        liquidacion_id: uuid.UUID,
        delegado_id: uuid.UUID,
    ) -> bool:
        """
        Elimina una asociación LiquidacionDelegado por liquidación + delegado.

        Args:
            liquidacion_id: UUID de la liquidación
            delegado_id: UUID del delegado

        Returns:
            True si se eliminó, False si no existía
        """
        deleted_count, _ = LiquidacionDelegado.objects.filter(
            liquidacion_id=liquidacion_id,
            delegado_id=delegado_id,
        ).delete()
        return deleted_count > 0

    # -------------------------------------------------------------------------
    # Helpers para Validaciones de Fase 3
    # -------------------------------------------------------------------------

    def _obtener_asignacion_municipal(
        self,
        delegado_id: uuid.UUID,
        municipalidad_id: uuid.UUID,
    ) -> Optional[MunicipalidadDelegado]:
        """
        Obtiene la asignación municipal de un delegado para una municipalidad.

        Este helper será usado por Fase 3 para validar que el delegado
        está asignado a la municipalidad de la liquidación.

        Args:
            delegado_id: UUID del delegado
            municipalidad_id: UUID de la municipalidad

        Returns:
            MunicipalidadDelegado o None si no existe
        """
        return MunicipalidadDelegado.objects.filter(
            delegado_id=delegado_id,
            municipalidad_id=municipalidad_id,
            activo=True,
        ).select_related('delegado', 'municipalidad').first()

    def _obtener_periodo_vigente(
        self,
        delegado_id: uuid.UUID,
        fecha_referencia: Optional[date] = None,
    ) -> Optional[PeriodoDelegado]:
        """
        Obtiene el periodo vigente de un delegado en una fecha dada.

        Este helper será usado por Fase 3 para validar que el delegado
        tiene un periodo vigente.

        Args:
            delegado_id: UUID del delegado
            fecha_referencia: Fecha a verificar (default: hoy)

        Returns:
            PeriodoDelegado o None si no hay periodo vigente
        """
        if fecha_referencia is None:
            from django.utils import timezone
            fecha_referencia = timezone.now().date()

        return PeriodoDelegado.objects.filter(
            delegado_id=delegado_id,
            periodo_inicio__lte=fecha_referencia,
        ).filter(
            models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha_referencia)
        ).order_by('-periodo_inicio').first()

    def _es_delegado_activo(self, delegado_id: uuid.UUID) -> bool:
        """
        Verifica si un delegado está activo.

        Args:
            delegado_id: UUID del delegado

        Returns:
            True si está activo, False otherwise
        """
        from modules.liquidaciones.domain.constants import DelegadoStatus
        return Delegado.objects.filter(
            id=delegado_id,
            status=DelegadoStatus.ACTIVO,
        ).exists()

    def _obtener_categoria_delegado(self, delegado_id: uuid.UUID) -> Optional[str]:
        """
        Obtiene la categoría de un delegado desde su asignación municipal.

        Args:
            delegado_id: UUID del delegado

        Returns:
            Categoría del delegado o None si no tiene asignación
        """
        asignacion = MunicipalidadDelegado.objects.filter(
            delegado_id=delegado_id,
        ).order_by('-activo', '-created_at').first()

        if asignacion:
            return asignacion.categoria
        return None

    def _verificar_categoria_valida_para_tipo_liquidacion(
        self,
        categoria_delegado: Optional[str],
        tipo_liquidacion: str,
    ) -> bool:
        """
        Verifica si la categoría del delegado es válida para el tipo de liquidación.

        Args:
            categoria_delegado: Categoría del delegado
            tipo_liquidacion: Tipo de liquidación (ej. EDIFICACION)

        Returns:
            True si es válida, False otherwise
        """
        if not categoria_delegado:
            return False

        # Mapeo de tipo_liquidacion a categoria requerida
        categoria_por_tipo = {
            'EDIFICACION': CategoriaDelegado.EDIFICACIONES,
            'HABILITACION_URBANA': CategoriaDelegado.HABILITACIONES_URBANAS,
        }

        categoria_requerida = categoria_por_tipo.get(tipo_liquidacion)
        if not categoria_requerida:
            # Si no hay mapeo definido, no se valida categoría
            return True

        return categoria_delegado == categoria_requerida


# Instancia singleton para uso directo
liquidacion_delegado_core = LiquidacionDelegadoCore()
