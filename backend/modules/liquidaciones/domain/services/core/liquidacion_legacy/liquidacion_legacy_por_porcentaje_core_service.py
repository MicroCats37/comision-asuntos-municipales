"""
LiquidacionLegacyPorPorcentajeCoreService — consultas ORM para liquidaciones legacy basadas en PO.

ORM PURO — sin lógica de negocio.
Maneja: TarifaPorcentajeObra, DerechoPorcentajeObra resuelto por fecha_registro.

Usado por flujos legacy para edificaciones, taludes e impacto-vial
(todos usan tarifas de porcentaje de valor de construcción).
"""
from datetime import date

from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class LiquidacionLegacyPorPorcentajeCoreService:
    """
    Core service for legacy PO (Porcentaje de Obra) tariff queries resolved by date.

    All methods are pure ORM — no business logic, no conditionals.
    """

    @inject
    def __init__(self, tarifas_service: TarifasHistoricasCoreService) -> None:
        self._tarifas_service = tarifas_service

    def get_tarifa_por_fecha(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> list[TarifaPorcentajeObra]:
        """
        Get all TarifaPorcentajeObra records vigentes at the given fecha for a tipo_liquidacion.

        Resolution path:
        1. TarifaLiquidacionBase.objects.vigentes(fecha=fecha) filtered by tipo_liquidacion
        2. Join child TarifaPorcentajeObra via tarifa_base FK

        Returns an empty list if no base tariff is vigentes at fecha.
        """
        tarifas_base = self._tarifas_service.get_tarifas_vigentes(tipo_liquidacion, fecha)
        if not tarifas_base:
            return []
        return self._tarifas_service.get_tarifas_porcentaje_obra_por_base(
            [tb.id for tb in tarifas_base]
        )

    def get_derecho_porcentaje_por_fecha(
        self,
        fecha: date,
    ) -> DerechoPorcentajeObra | None:
        """
        Get the DerechoPorcentajeObra vigente at the given fecha.

        Uses DerechoPorcentajeObra.objects.vigentes(fecha=fecha) which applies
        the standard VigenciaModel filter (periodo_inicio__lte=fecha and
        periodo_fin__isnull or periodo_fin__gte=fecha).

        Returns None if no derecho is vigente at fecha.
        """
        derechos = self._tarifas_service.get_derechos_porcentaje_vigentes(fecha)
        return derechos[0] if derechos else None

    def get_derechos_porcentaje_list(self, fecha: date) -> list[DerechoPorcentajeObra]:
        """
        Returns the raw list of DerechoPorcentajeObra vigentes at fecha.
        Used by legacy orchestrators for overlap validation before [0] selection.
        """
        return self._tarifas_service.get_derechos_porcentaje_vigentes(fecha)
