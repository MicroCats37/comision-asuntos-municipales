"""
Shared validation helpers for PorcentajeObra (PO) orchestrators.

Contains duplicated validation methods extracted from:
- LiquidacionEdificacionesOrchestrator
- LiquidacionTaludesOrchestrator
- LiquidacionImpactoVialOrchestrator

These remain in the ORCHESTRATOR layer (validation + HttpError) — NOT in core.
"""
from django.db import models
from django.utils import timezone
from ninja.errors import HttpError

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)


class LiquidacionPOValidationMixin:
    """
    Mixin providing shared validation methods for PO-type orchestrators.

    Usage: class MyOrchestrator(LiquidacionPOValidationMixin, ...):
        ...

    The validation logic STAYS in the orchestrator (raises HttpError).
    These are NOT moved to core (core is pure ORM mapping, no business logic).
    """

    def _validar_tarifa_explicita(
        self, tarifa, tipo_liquidacion: str, fecha=None
    ) -> None:
        """
        Validates an explicitly-provided tarifa in the input.
        Raises HttpError if invalid.

        Args:
            tarifa: TarifaPorcentajeObra ORM object
            tipo_liquidacion: TipoLiquidacion constant string (e.g. 'EDIFICACION')
            fecha: Date used to check vigencia. Defaults to today (flujo normal).
                   El flujo legacy pasa fecha_registro para validar la tarifa
                   vigente en esa fecha histórica, no contra hoy.
        """
        fecha = fecha if fecha is not None else timezone.now().date()
        is_vigente = (
            tarifa.tarifa_base.periodo_inicio <= fecha
            and (
                tarifa.tarifa_base.periodo_fin is None
                or tarifa.tarifa_base.periodo_fin >= fecha
            )
        )
        if not is_vigente:
            raise HttpError(400, "Tarifa no está vigente.")
        if tarifa.tarifa_base.tipo_liquidacion.codigo != tipo_liquidacion:
            raise HttpError(400, "Tarifa no es del tipo esperado.")

    def _obtener_especialidades_vigentes_para_tipo(
        self, tipo_liquidacion: str, fecha: "date | None" = None
    ):
        """
        Fetches vigentes LiquidacionEspecialidadDisponibles for the given tipo_liquidacion.
        Returns list of LiquidacionEspecialidadDisponibles ORM objects.

        Args:
            tipo_liquidacion: TipoLiquidacion constant string (e.g. 'EDIFICACION')
            fecha: Date to use for period filter. Defaults to timezone.now().date() if None.

        Returns:
            List of LiquidacionEspecialidadDisponibles objects
        """
        fecha = fecha if fecha is not None else timezone.now().date()
        return list(
            LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion__codigo=tipo_liquidacion,
                activo=True,
                periodo_inicio__lte=fecha,
            ).filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            ).select_related("especialidad")
        )
