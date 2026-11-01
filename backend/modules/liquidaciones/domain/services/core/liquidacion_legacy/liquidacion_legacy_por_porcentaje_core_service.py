"""
LiquidacionLegacyPorPorcentajeCoreService — consultas ORM para liquidaciones legacy basadas en PO.

Adaptador sobre el resolver canónico (LiquidacionHistoricoCoreService).
La resolución histórica (tarifas base, porcentajes de obra y derechos) la
realiza exclusivamente el resolver canónico; este adaptador solo conserva el
contrato nullable que consumen los importadores legacy.

Usado por flujos legacy para edificaciones, taludes e impacto-vial
(todos usan tarifas de porcentaje de valor de construcción).
"""
from datetime import date

from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class LiquidacionLegacyPorPorcentajeCoreService:
    """
    Core service for legacy PO (Porcentaje de Obra) tariff queries resolved by date.

    Historical reads are delegated to the canonical resolver
    (LiquidacionHistoricoCoreService); this adapter preserves the nullable
    return contract expected by the legacy importers.

    `tarifas_service` remains the injection point (and the constructor keyword
    used by the legacy import commands) so the importer contracts stay intact.
    """

    @inject
    def __init__(self, tarifas_service: TarifasHistoricasCoreService) -> None:
        self._historico = LiquidacionHistoricoCoreService(tarifas_service=tarifas_service)

    def get_tarifa_por_fecha(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> list[TarifaPorcentajeObra]:
        """
        Get all TarifaPorcentajeObra records vigentes at the given fecha for a tipo_liquidacion.

        Resolution path (delegated to the canonical resolver):
        1. TarifaLiquidacionBase vigentes at fecha for the tipo_liquidacion
        2. Join child TarifaPorcentajeObra via tarifa_base FK

        Returns an empty list if no base tariff is vigente at fecha.
        """
        tarifas_base = self._historico.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        if not tarifas_base:
            return []
        return self._historico.get_tarifa_porcentaje_obra(
            [str(tb.id) for tb in tarifas_base]
        )

    def get_derecho_porcentaje_por_fecha(
        self,
        fecha: date,
    ) -> DerechoPorcentajeObra | None:
        """
        Get the DerechoPorcentajeObra vigente at the given fecha.

        Returns None if no derecho is vigente at fecha.
        """
        derechos = self._historico.get_derechos_porcentaje_vigentes(fecha)
        return derechos[0] if derechos else None

    def get_derechos_porcentaje_list(self, fecha: date) -> list[DerechoPorcentajeObra]:
        """
        Returns the raw list of DerechoPorcentajeObra vigentes at fecha.
        Used by legacy orchestrators for overlap validation before [0] selection.
        """
        return self._historico.get_derechos_porcentaje_vigentes(fecha)
