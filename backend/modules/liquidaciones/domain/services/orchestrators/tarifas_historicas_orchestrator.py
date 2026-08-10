"""
TarifasHistoricasOrchestrator — Orchestrator for historical tariff queries.

Validates input and delegates to Core. Constructs Domain DTOs.
"""
from datetime import date
from typing import List, Tuple
from injector import inject

from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from modules.liquidaciones.domain.results.tarifas_historicas_results import (
    TarifaHistoricaPeriodoResult,
    TarifaPorcentajeObraDetalleResult,
    TarifaM2Result,
    TarifaVisitasResult,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, KIND_SLUG_TO_TIPO_LIQUIDACION


# Types that use PorcentajeObra (multiple tarifas per base by especialidad)
TIPO_LIQUIDACION_PORCENTAJE = {
    TipoLiquidacion.EDIFICACION,
    TipoLiquidacion.IMPACTO_VIAL,
    TipoLiquidacion.TALUDES,
}

# Types that use M2 (OneToOne: one tarifa per base)
TIPO_LIQUIDACION_M2 = {
    TipoLiquidacion.HABILITACION_URBANA,
    TipoLiquidacion.MECANICA_SUELOS,
}

# Types that use Visitas (multiple categorias per base)
TIPO_LIQUIDACION_VISITAS = {
    TipoLiquidacion.INSPECCION_OBRA,
}


class TarifasHistoricasOrchestrator:
    @inject
    def __init__(
        self,
        core_service: TarifasHistoricasCoreService,
    ):
        self.core_service = core_service

    def _normalize_tipo(self, tipo: str) -> str:
        """Normalize tipo_liquidacion from slug or enum to enum value."""
        return normalizar_tipo_liquidacion(tipo)

    def obtener_tarifas_historicas_proceso(
        self,
        tipo: str,
        fecha_desde: date,
        fecha_hasta: date,
        page: int,
        page_size: int,
    ) -> Tuple[List[TarifaHistoricaPeriodoResult], int]:
        """
        Fetch historical tariffs for a tipo_liquidacion within date range.
        
        Returns (list of TarifaHistoricaPeriodoResult, total_count).
        """
        # Normalize tipo
        tipo_normalized = self._normalize_tipo(tipo)
        
        # Pagination defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        # Query historical bases
        bases, total = self.core_service.get_tarifas_historicas(
            tipo_liquidacion=tipo_normalized,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            page_size=page_size,
        )

        if not bases:
            return [], total

        base_ids = [str(b.id) for b in bases]

        # Fetch detail records based on tipo
        if tipo_normalized in TIPO_LIQUIDACION_PORCENTAJE:
            detalle_raw = self.core_service.get_tarifas_porcentaje_obra_por_base(base_ids)
            # Group by base
            detalle_map: dict[str, list] = {}
            for d in detalle_raw:
                key = str(d.tarifa_base_id)
                if key not in detalle_map:
                    detalle_map[key] = []
                detalle_map[key].append(TarifaPorcentajeObraDetalleResult(
                    id=d.id,
                    especialidad_id=d.especialidad.id,
                    especialidad_nombre=d.especialidad.nombre,
                    porcentaje_liquidacion=float(d.porcentaje_liquidacion),
                ))
        elif tipo_normalized in TIPO_LIQUIDACION_M2:
            detalle_map = {}
            for bid in base_ids:
                m2 = self.core_service.get_tarifa_m2_por_base(bid)
                if m2:
                    detalle_map[bid] = TarifaM2Result(
                        id=m2.id,
                        costo_por_m2=float(m2.costo_por_m2),
                    )
        elif tipo_normalized in TIPO_LIQUIDACION_VISITAS:
            detalle_raw = self.core_service.get_tarifas_categoria_visitas_por_base(base_ids)
            detalle_map = {}
            for d in detalle_raw:
                key = str(d.tarifa_base_id)
                if key not in detalle_map:
                    detalle_map[key] = []
                detalle_map[key].append(TarifaVisitasResult(
                    id=d.id,
                    categoria=d.categoria_visitas,
                    porcentaje_uit=float(d.porcentaje_uit),
                ))
        else:
            detalle_map = {}

        # Build result DTOs
        resultados: List[TarifaHistoricaPeriodoResult] = []
        for base in bases:
            bid = str(base.id)
            
            if tipo_normalized in TIPO_LIQUIDACION_PORCENTAJE:
                tarifas_porcentaje = detalle_map.get(bid, [])
                tarifas_m2 = None
                tarifas_visitas = []
            elif tipo_normalized in TIPO_LIQUIDACION_M2:
                tarifas_porcentaje = []
                tarifas_m2 = detalle_map.get(bid)
                tarifas_visitas = []
            else:  # VISITAS
                tarifas_porcentaje = []
                tarifas_m2 = None
                tarifas_visitas = detalle_map.get(bid, [])

            resultados.append(TarifaHistoricaPeriodoResult(
                id=base.id,
                tipo_liquidacion=base.tipo_liquidacion,
                periodo_inicio=base.periodo_inicio,
                periodo_fin=base.periodo_fin,
                tarifas_porcentaje=tarifas_porcentaje,
                tarifa_m2=tarifas_m2,
                tarifas_visitas=tarifas_visitas,
            ))

        return resultados, total


def normalizar_tipo_liquidacion(tipo_liquidacion: str) -> str:
    """
    Normalizes a tipo_liquidacion from slug or enum to enum value.
    """
    if tipo_liquidacion in TipoLiquidacion.values:
        return tipo_liquidacion
    if tipo_liquidacion in KIND_SLUG_TO_TIPO_LIQUIDACION:
        return KIND_SLUG_TO_TIPO_LIQUIDACION[tipo_liquidacion]
    return tipo_liquidacion