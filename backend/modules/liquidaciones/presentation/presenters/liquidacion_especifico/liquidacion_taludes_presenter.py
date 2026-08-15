"""
Presenter for Taludes (PorcentajeObra).

@staticmethod only. Maps Domain Result -> Presentation Schema.
"""
import math
import uuid
from typing import List

from modules.liquidaciones.domain.results.liquidacion_especifico.taludes_primera_revision_result import (
    TaludesPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_taludes_schemas import (
    LiquidacionTaludesOutput,
    LiquidacionTaludesCotizarOutput,
    LiquidacionTaludesCotizarDetalleOut,
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
)
from core.pagination import PaginatedData


class LiquidacionTaludesPresenter:
    @staticmethod
    def present_primera_revision(domain_result: TaludesPrimeraRevisionResult) -> LiquidacionTaludesOutput:
        general = domain_result.liquidacion_general
        tipo = domain_result.liquidacion_tipo
        especifica = domain_result.liquidacion_especifica

        general_out = LiquidacionGeneralPresenter.present_liquidacion_general(general)

        tipo_out = LiquidacionTipoOutput(
            id=uuid.UUID(especifica.id),
            numero=especifica.numero,
        )

        tipo_datos_out = LiquidacionPorcentajeObraDatosOut(
            id=uuid.UUID(tipo.id),
            valor_declarado=tipo.valor_declarado,
            porcentaje_liquidacion=tipo.porcentaje_liquidacion,
            tipo_tramite=tipo.tipo_tramite,  # NULL
            derecho_minimo=tipo.derecho_minimo,
            derecho_maximo=tipo.derecho_maximo,
            porcentaje_minimo_uit=tipo.porcentaje_minimo_uit,
            derecho_aplicado_id=uuid.UUID(tipo.derecho_aplicado_id),
            detalles=[
                LiquidacionPorcentajeObraDetalleOut(
                    id=uuid.UUID(d.id),
                    tarifa_aplicada_id=uuid.UUID(d.tarifa_aplicada_id),
                    especialidad_id=uuid.UUID(d.especialidad_id),
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv,
                    uit=d.uit,
                    total=d.total,
                )
                for d in tipo.detalles
            ],
        )

        return LiquidacionTaludesOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=tipo_datos_out,
        )

    @staticmethod
    def present_cotizacion(domain_result: CotizacionPorcentajeObraResult) -> LiquidacionTaludesCotizarOutput:
        """
        Maps CotizacionPorcentajeObraResult to LiquidacionTaludesCotizarOutput.
        """
        return LiquidacionTaludesCotizarOutput(
            valor_declarado=domain_result.valor_declarado,
            porcentaje_liquidacion=domain_result.porcentaje_liquidacion,
            derecho_minimo=domain_result.derecho_minimo,
            derecho_maximo=domain_result.derecho_maximo,
            porcentaje_minimo_uit=domain_result.porcentaje_minimo_uit,
            derecho_aplicado_id=uuid.UUID(domain_result.derecho_aplicado_id),
            detalles=[
                LiquidacionTaludesCotizarDetalleOut(
                    tarifa_id=uuid.UUID(d.tarifa_id),
                    especialidad_id=uuid.UUID(d.especialidad_id),
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv,
                    uit=d.uit,
                    total=d.total,
                )
                for d in domain_result.detalles
            ],
            total_subtotal=domain_result.total_subtotal,
            total=domain_result.total,
        )

    @staticmethod
    def present_list(
        liquidaciones: List[TaludesPrimeraRevisionResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionTaludesOutput]:
        """
        Maps a list of TaludesPrimeraRevisionResult domain DTOs to PaginatedData[LiquidacionTaludesOutput].

        Each item is presented by calling present_primera_revision.
        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionTaludesOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionTaludesPresenter.present_primera_revision(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(domain_result: TaludesPrimeraRevisionResult) -> LiquidacionTaludesOutput:
        """
        Maps a single TaludesPrimeraRevisionResult domain DTO to LiquidacionTaludesOutput.
        Delegates to present_primera_revision.
        """
        return LiquidacionTaludesPresenter.present_primera_revision(domain_result)

    @staticmethod
    def present_tarifas_vigentes(tarifas, especialidades_disponibles) -> dict:
        """
        Maps TarifaPorcentajeObra domain objects and LiquidacionEspecialidadDisponibles
        to a dict response (motor PorcentajeObra).

        Delegates to the shared PO helper to avoid duplication across
        edificaciones/taludes/impacto_vial.
        """
        from modules.liquidaciones.presentation.presenters._shared.po_tarifas_presenter import (
            present_tarifas_vigentes_po,
        )

        return present_tarifas_vigentes_po(tarifas, especialidades_disponibles)
