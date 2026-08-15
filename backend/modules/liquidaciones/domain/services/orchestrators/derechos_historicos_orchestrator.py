"""
DerechosHistoricosOrchestrator — Orchestrator for historical derechos queries.

Validates input and delegates to Core. Constructs Domain DTOs.
"""
from datetime import date
from typing import List, Union
from injector import inject

from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from modules.liquidaciones.domain.results.tarifas_historicas_results import (
    DerechoHistoricoResult,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)


class DerechosHistoricosOrchestrator:
    @inject
    def __init__(
        self,
        core_service: TarifasHistoricasCoreService,
    ):
        self.core_service = core_service

    def _map_derecho(self, d: Union[DerechoPorcentajeObra, DerechoPorMetroCuadrado]) -> DerechoHistoricoResult:
        """Map a derecho model to DerechoHistoricoResult."""
        # Only DerechoPorcentajeObra has porcentaje_minimo_uit
        porcentaje_minimo_uit = None
        if isinstance(d, DerechoPorcentajeObra):
            porcentaje_minimo_uit = float(d.porcentaje_minimo_uit) if d.porcentaje_minimo_uit is not None else None

        return DerechoHistoricoResult(
            id=d.id,
            derecho_minimo=float(d.derecho_minimo) if d.derecho_minimo is not None else None,
            derecho_maximo=float(d.derecho_maximo) if d.derecho_maximo is not None else None,
            porcentaje_minimo_uit=porcentaje_minimo_uit,
            periodo_inicio=d.periodo_inicio,
            periodo_fin=d.periodo_fin,
        )

    def obtener_derechos_historicos_proceso(
        self,
        tipo: str,
        fecha_desde: date = None,
        fecha_hasta: date = None,
    ) -> List[DerechoHistoricoResult]:
        """
        Fetch derechos (PORCENTAJE or METRO_CUADRADO).

        If both fecha_desde and fecha_hasta are given: historical range query.
        Otherwise: vigentes at the reference date (the provided one, or today).
        """
        if tipo == "PORCENTAJE":
            if fecha_desde is not None and fecha_hasta is not None:
                derechos = self.core_service.get_derechos_porcentaje_historicos(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            else:
                fecha_ref = fecha_desde if fecha_desde is not None else fecha_hasta
                derechos = self.core_service.get_derechos_porcentaje_vigentes(fecha=fecha_ref)
        elif tipo == "METRO_CUADRADO":
            if fecha_desde is not None and fecha_hasta is not None:
                derechos = self.core_service.get_derechos_m2_historicos(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            else:
                fecha_ref = fecha_desde if fecha_desde is not None else fecha_hasta
                derechos = self.core_service.get_derechos_m2_vigentes(fecha=fecha_ref)
        else:
            derechos = []

        return [self._map_derecho(d) for d in derechos]