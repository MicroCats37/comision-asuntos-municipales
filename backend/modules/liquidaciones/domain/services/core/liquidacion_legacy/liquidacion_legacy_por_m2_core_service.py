"""
LiquidacionLegacyPorM2CoreService — consultas ORM para liquidaciones legacy basadas en M2.

Adaptador sobre el resolver canónico (LiquidacionHistoricoCoreService).
La resolución histórica (tarifas base, metros cuadrados y derechos) la realiza
exclusivamente el resolver canónico; este adaptador solo conserva el contrato
nullable que consumen los importadores legacy.

Usado por flujos legacy para habilitación urbana y mecánica de suelos
(ambos usan tarifas por metro cuadrado).
"""
from datetime import date

from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorMetroCuadrado,
    TarifaPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class LiquidacionLegacyPorM2CoreService:
    """
    Core service for legacy M2 (metro cuadrado) tariff queries resolved by date.

    Historical reads are delegated to the canonical resolver
    (LiquidacionHistoricoCoreService); this adapter preserves the nullable
    return contract expected by the legacy importers.

    `tarifas_service` remains the injection point (and the constructor keyword
    used by the legacy import commands) so the importer contracts stay intact.
    """

    @inject
    def __init__(self, tarifas_service: TarifasHistoricasCoreService) -> None:
        self._historico = LiquidacionHistoricoCoreService(tarifas_service=tarifas_service)

    def get_tarifa_m2_por_fecha(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaPorMetroCuadrado | None:
        """
        Get the TarifaPorMetroCuadrado vigentes at the given fecha for a tipo_liquidacion.

        Resolution path (delegated to the canonical resolver):
        1. TarifaLiquidacionBase vigentes at fecha for the tipo_liquidacion
        2. Join child TarifaPorMetroCuadrado via OneToOneField tarifa_base

        Returns None if no base tariff or no child M2 record is vigente at fecha.
        """
        tarifas_base = self._historico.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
        if not tarifas_base:
            return None
        # There should be exactly one base for a given tipo_liquidacion at a given fecha.
        # Use the first one found (most recent inicio).
        base = tarifas_base[0]
        return self._historico.get_tarifa_m2(str(base.id))

    def get_derecho_m2_por_fecha(
        self,
        fecha: date,
    ) -> DerechoPorMetroCuadrado | None:
        """
        Get the DerechoPorMetroCuadrado vigente at the given fecha.

        Returns None if no derecho is vigente at fecha.
        """
        derechos = self._historico.get_derechos_m2_vigentes(fecha)
        return derechos[0] if derechos else None

    def get_derechos_m2_list(self, fecha: date) -> list[DerechoPorMetroCuadrado]:
        """
        Returns the raw list of DerechoPorMetroCuadrado vigentes at fecha.
        Used by legacy orchestrators for overlap validation before [0] selection.
        """
        return self._historico.get_derechos_m2_vigentes(fecha)

    def get_tarifas_base_list(self, tipo_liquidacion: str, fecha: date) -> list:
        """
        Returns the raw list of TarifaLiquidacionBase vigentes at fecha for a tipo.
        Used by legacy orchestrators for overlap validation.
        """
        return self._historico.get_tarifa_base_vigente_list(tipo_liquidacion, fecha)
