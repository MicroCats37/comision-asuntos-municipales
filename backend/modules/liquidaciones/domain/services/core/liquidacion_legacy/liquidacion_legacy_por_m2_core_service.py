"""
LiquidacionLegacyPorM2CoreService — ORM queries for legacy M2-based liquidations.

PURE ORM — no business logic.
Handles: TarifaPorMetroCuadrado, DerechoPorMetroCuadrado resolved by fecha_registro.

Used by legacy flows for habilitación urbana and mecánica de suelos
(which both use square-meter tariffs).
"""
from typing import Optional
from datetime import date

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class LiquidacionLegacyPorM2CoreService:
    """
    Core service for legacy M2 (metro cuadrado) tariff queries resolved by date.

    All methods are pure ORM — no business logic, no conditionals.
    """

    def __init__(self) -> None:
        self._tarifas_service = TarifasHistoricasCoreService()

    def get_tarifa_m2_por_fecha(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> Optional[TarifaPorMetroCuadrado]:
        """
        Get the TarifaPorMetroCuadrado vigentes at the given fecha for a tipo_liquidacion.

        Resolution path:
        1. TarifaLiquidacionBase.objects.vigentes(fecha=fecha) filtered by tipo_liquidacion
        2. Join child TarifaPorMetroCuadrado via OneToOneField tarifa_base

        Returns None if no base tariff or no child M2 record is vigente at fecha.
        """
        tarifas_base = self._tarifas_service.get_tarifas_vigentes(tipo_liquidacion, fecha)
        if not tarifas_base:
            return None
        # There should be exactly one base for a given tipo_liquidacion at a given fecha.
        # Use the first one found (most recent inicio).
        base = tarifas_base[0]
        return self._tarifas_service.get_tarifa_m2_por_base(base.id)

    def get_derecho_m2_por_fecha(
        self,
        fecha: date,
    ) -> Optional[DerechoPorMetroCuadrado]:
        """
        Get the DerechoPorMetroCuadrado vigente at the given fecha.

        Uses DerechoPorMetroCuadrado.objects.vigentes(fecha=fecha) which applies
        the standard VigenciaModel filter (periodo_inicio__lte=fecha and
        periodo_fin__isnull or periodo_fin__gte=fecha).

        Returns None if no derecho is vigente at fecha.
        """
        derechos = self._tarifas_service.get_derechos_m2_vigentes(fecha)
        return derechos[0] if derechos else None
