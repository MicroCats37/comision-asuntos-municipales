"""
LiquidacionMecanicaSuelosPresenter — Presenter específico para Mecánica de Suelos.

Solo mapea la primera-revisión (ensamblaje final).
Cotizar y tarifas vigentes se delegan al LiquidacionPorMetroCuadradoPresenter.
NO business logic.
"""
import uuid
import math
from typing import List

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
    LiquidacionPorMetroCuadradoDatosOut,
)
from core.pagination import PaginatedData

from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
    MecanicaSuelosPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
    LiquidacionM2Result,
)


class LiquidacionMecanicaSuelosPresenter:
    """
    Presenter específico para Mecánica de Suelos.
    Solo maneja el mapeo de primera-revisión.
    """

    @staticmethod
    def present_primera_revision(
        result: MecanicaSuelosPrimeraRevisionResult,
    ) -> LiquidacionMecanicaSuelosOutput:
        """Assembles the final Mecánica de Suelos output from the Result."""
        general = result.liquidacion_general
        tipo = result.liquidacion_tipo
        especifica = result.liquidacion_especifica

        general_out = LiquidacionGeneralPresenter.present_liquidacion_general(general)

        tipo_out = LiquidacionTipoOutput(
            id=uuid.UUID(especifica.id),
            numero=especifica.numero,
        )

        especifica_out = LiquidacionPorMetroCuadradoDatosOut(
            id=uuid.UUID(tipo.id),
            area_m2=tipo.area_m2,
            costo_por_m2=tipo.costo_por_m2,
            derecho_minimo=tipo.derecho_minimo,
            derecho_maximo=tipo.derecho_maximo,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id) if tipo.tarifa_aplicada_id else None,
            derecho_aplicado_id=uuid.UUID(tipo.derecho_aplicado_id) if tipo.derecho_aplicado_id else None,
        )

        return LiquidacionMecanicaSuelosOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=especifica_out,
        )

    @staticmethod
    def present_list(
        liquidaciones: List[MecanicaSuelosPrimeraRevisionResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionMecanicaSuelosOutput]:
        """
        Maps a list of MecanicaSuelosPrimeraRevisionResult domain DTOs to PaginatedData[LiquidacionMecanicaSuelosOutput].

        Each item is presented by calling present_primera_revision.
        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionMecanicaSuelosOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionMecanicaSuelosPresenter.present_primera_revision(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(domain_result: MecanicaSuelosPrimeraRevisionResult) -> LiquidacionMecanicaSuelosOutput:
        """
        Maps a single MecanicaSuelosPrimeraRevisionResult domain DTO to LiquidacionMecanicaSuelosOutput.
        Delegates to present_primera_revision.
        """
        return LiquidacionMecanicaSuelosPresenter.present_primera_revision(domain_result)
