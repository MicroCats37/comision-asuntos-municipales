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
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, KIND_SLUG_TO_TIPO_LIQUIDACION
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import validar_sin_solapamiento


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
        fecha_desde: date = None,
        fecha_hasta: date = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[TarifaHistoricaPeriodoResult], int]:
        """
        Fetch tariffs for a tipo_liquidacion.

        If both fecha_desde and fecha_hasta are given: historical range query.
        Otherwise: vigentes at the reference date (the provided one, or today).
        Pagination applies over the tariff bases in both modes.

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

        # Query bases: historical range or vigentes at reference date
        if fecha_desde is not None and fecha_hasta is not None:
            bases, total = self.core_service.get_tarifas_historicas(
                tipo_liquidacion=tipo_normalized,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                page_size=page_size,
            )
        else:
            fecha_ref = fecha_desde if fecha_desde is not None else fecha_hasta
            all_bases = self.core_service.get_tarifas_vigentes(
                tipo_liquidacion=tipo_normalized,
                fecha=fecha_ref,
            )
            validar_sin_solapamiento(all_bases, f"TarifaLiquidacionBase tipo={tipo_normalized}")
            total = len(all_bases)
            offset = (page - 1) * page_size
            bases = all_bases[offset:offset + page_size]

        if not bases:
            return [], total

        base_ids = [str(b.id) for b in bases]

        # Fetch detail records based on tipo
        if tipo_normalized in TIPO_LIQUIDACION_PORCENTAJE:
            detalle_raw = self.core_service.get_tarifas_porcentaje_obra_por_base(base_ids)
            # With tarifa-unica-especialidades: TarifaPorcentajeObra no longer has especialidad FK.
            # Each tariff applies to ALL LiquidacionEspecialidadDisponibles for the tipo_liquidacion.
            # Fetch them and expand: 1 tariff × N especialidades = N detail results.
            from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
                LiquidacionEspecialidadDisponibles,
            )
            from django.db.models import Q
            from django.utils import timezone
            today = timezone.now().date()
            especialidades = LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion__codigo=tipo_normalized,
                activo=True,
                periodo_inicio__lte=today,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today)
            ).select_related("especialidad")
            # Group by base
            detalle_map: dict[str, list] = {}
            for d in detalle_raw:
                key = str(d.tarifa_base_id)
                if key not in detalle_map:
                    detalle_map[key] = []
                # Expand: 1 tariff × N especialidades
                for esp in especialidades:
                    detalle_map[key].append(TarifaPorcentajeObraDetalleResult(
                        id=d.id,
                        especialidad_id=esp.especialidad.id,
                        especialidad_nombre=esp.especialidad.nombre,
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
                tipo_liquidacion=base.tipo_liquidacion.codigo,
                periodo_inicio=base.periodo_inicio,
                periodo_fin=base.periodo_fin,
                tarifas_porcentaje=tarifas_porcentaje,
                tarifa_m2=tarifas_m2,
                tarifas_visitas=tarifas_visitas,
            ))

        return resultados, total

    # ── General (all tipos) ─────────────────────────────────────────────────────

    def obtener_tarifas_generales_proceso(
        self,
        fecha_desde: date = None,
        fecha_hasta: date = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[TarifaHistoricaPeriodoResult], int]:
        """
        Fetch ALL historical tariff bases across every tipo_liquidacion.

        If both fecha_desde and fecha_hasta are given: historical range query.
        Otherwise: vigentes at the reference date (the provided one, or today).
        Pagination applies over the tariff bases in both modes.

        Returns (list of TarifaHistoricaPeriodoResult, total_count).
        """
        # Pagination defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        # Query bases: historical range or vigentes at reference date
        if fecha_desde is not None and fecha_hasta is not None:
            bases, total = self.core_service.get_tarifas_generales_historicas(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=page,
                page_size=page_size,
            )
        else:
            fecha_ref = fecha_desde if fecha_desde is not None else fecha_hasta
            all_bases = self.core_service.get_tarifas_generales_vigentes(fecha=fecha_ref)
            total = len(all_bases)
            offset = (page - 1) * page_size
            bases = all_bases[offset:offset + page_size]

        if not bases:
            return [], total

        # Build result DTOs using the shared detail assembly helper
        resultados = self._armar_resultados_desde_bases(bases)
        return resultados, total

    def _armar_resultados_desde_bases(
        self,
        bases: List[TarifaLiquidacionBase],
    ) -> List[TarifaHistoricaPeriodoResult]:
        """
        Shared helper: given a list of TarifaLiquidacionBase (any mix of tipos),
        fetch their detail records and assemble TarifaHistoricaPeriodoResult DTOs.

        Works for both single-tipo and multi-tipo (general) queries.
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
            LiquidacionEspecialidadDisponibles,
        )
        from django.db.models import Q
        from django.utils import timezone

        resultados: List[TarifaHistoricaPeriodoResult] = []
        if not bases:
            return resultados

        base_ids = [str(b.id) for b in bases]

        # Collect the tipos present in this batch
        tipos_presentes = {b.tipo_liquidacion.codigo for b in bases}

        # ── Fetch detail records per tipo ──────────────────────────────────────
        detalle_porcentaje_map: dict[str, list] = {}
        detalle_m2_map: dict[str, TarifaM2Result] = {}
        detalle_visitas_map: dict[str, list] = {}
        especialidades_por_tipo: dict[str, list] = {}

        for tipo_codigo in tipos_presentes:
            if tipo_codigo in TIPO_LIQUIDACION_PORCENTAJE:
                raw = self.core_service.get_tarifas_porcentaje_obra_por_base(base_ids)
                today = timezone.now().date()
                especialidades = LiquidacionEspecialidadDisponibles.objects.filter(
                    tipo_liquidacion__codigo=tipo_codigo,
                    activo=True,
                    periodo_inicio__lte=today,
                ).filter(
                    Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today)
                ).select_related("especialidad")
                especialidades_por_tipo[tipo_codigo] = list(especialidades)
                for d in raw:
                    key = str(d.tarifa_base_id)
                    if key not in detalle_porcentaje_map:
                        detalle_porcentaje_map[key] = []
                    for esp in especialidades_por_tipo[tipo_codigo]:
                        detalle_porcentaje_map[key].append(
                            TarifaPorcentajeObraDetalleResult(
                                id=d.id,
                                especialidad_id=esp.especialidad.id,
                                especialidad_nombre=esp.especialidad.nombre,
                                porcentaje_liquidacion=float(d.porcentaje_liquidacion),
                            )
                        )
            elif tipo_codigo in TIPO_LIQUIDACION_M2:
                for bid in base_ids:
                    m2 = self.core_service.get_tarifa_m2_por_base(bid)
                    if m2:
                        detalle_m2_map[bid] = TarifaM2Result(
                            id=m2.id,
                            costo_por_m2=float(m2.costo_por_m2),
                        )
            elif tipo_codigo in TIPO_LIQUIDACION_VISITAS:
                raw = self.core_service.get_tarifas_categoria_visitas_por_base(base_ids)
                for d in raw:
                    key = str(d.tarifa_base_id)
                    if key not in detalle_visitas_map:
                        detalle_visitas_map[key] = []
                    detalle_visitas_map[key].append(
                        TarifaVisitasResult(
                            id=d.id,
                            categoria=d.categoria_visitas,
                            porcentaje_uit=float(d.porcentaje_uit),
                        )
                    )

        # ── Assemble result DTOs ──────────────────────────────────────────────
        for base in bases:
            bid = str(base.id)
            tipo_codigo = base.tipo_liquidacion.codigo

            if tipo_codigo in TIPO_LIQUIDACION_PORCENTAJE:
                tarifas_porcentaje = detalle_porcentaje_map.get(bid, [])
                tarifas_m2 = None
                tarifas_visitas = []
            elif tipo_codigo in TIPO_LIQUIDACION_M2:
                tarifas_porcentaje = []
                tarifas_m2 = detalle_m2_map.get(bid)
                tarifas_visitas = []
            else:  # VISITAS
                tarifas_porcentaje = []
                tarifas_m2 = None
                tarifas_visitas = detalle_visitas_map.get(bid, [])

            resultados.append(TarifaHistoricaPeriodoResult(
                id=base.id,
                tipo_liquidacion=tipo_codigo,
                periodo_inicio=base.periodo_inicio,
                periodo_fin=base.periodo_fin,
                tarifas_porcentaje=tarifas_porcentaje,
                tarifa_m2=tarifas_m2,
                tarifas_visitas=tarifas_visitas,
            ))

        return resultados


def normalizar_tipo_liquidacion(tipo_liquidacion: str) -> str:
    """
    Normalizes a tipo_liquidacion from slug or enum to enum value.
    """
    if tipo_liquidacion in TipoLiquidacion.values:
        return tipo_liquidacion
    if tipo_liquidacion in KIND_SLUG_TO_TIPO_LIQUIDACION:
        return KIND_SLUG_TO_TIPO_LIQUIDACION[tipo_liquidacion]
    return tipo_liquidacion