"""
Presenter mixto para últimas revisiones generales.

Despacha cada DTO enriquecido hacia el presenter específico existente según el
tipo de liquidación incluido en liquidacion_general.tipo_liquidacion.
"""
import math
from typing import Any

from core.pagination import PaginatedData
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_edificaciones_presenter import (
    LiquidacionEdificacionesPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_habilitacion_urbana_presenter import (
    LiquidacionHabilitacionUrbanaPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_impacto_vial_presenter import (
    LiquidacionImpactoVialPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_inspeccion_obra_presenter import (
    LiquidacionInspeccionObraPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_mecanica_suelos_presenter import (
    LiquidacionMecanicaSuelosPresenter,
)
from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_taludes_presenter import (
    LiquidacionTaludesPresenter,
)


class LiquidacionMixedPresenter:
    _PRESENTER_MAP = {
        TipoLiquidacion.EDIFICACION: LiquidacionEdificacionesPresenter.present_primera_revision,
        TipoLiquidacion.HABILITACION_URBANA: LiquidacionHabilitacionUrbanaPresenter.present_primera_revision,
        TipoLiquidacion.MECANICA_SUELOS: LiquidacionMecanicaSuelosPresenter.present_primera_revision,
        TipoLiquidacion.TALUDES: LiquidacionTaludesPresenter.present_primera_revision,
        TipoLiquidacion.IMPACTO_VIAL: LiquidacionImpactoVialPresenter.present_primera_revision,
        TipoLiquidacion.INSPECCION_OBRA: LiquidacionInspeccionObraPresenter.present_primera_revision,
    }

    @classmethod
    def present_item(cls, result) -> Any:
        codigo = result.liquidacion_general.tipo_liquidacion.codigo
        presenter = cls._PRESENTER_MAP.get(codigo)
        if presenter is None:
            raise ValueError(f"No hay presenter configurado para tipo_liquidacion={codigo}")
        return presenter(result)

    @classmethod
    def present_list(
        cls,
        liquidaciones: list,
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[Any]:
        return PaginatedData(
            items=[cls.present_item(result) for result in liquidaciones],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        )
