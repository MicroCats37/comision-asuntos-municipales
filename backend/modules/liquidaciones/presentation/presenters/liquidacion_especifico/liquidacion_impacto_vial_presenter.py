"""
Presenter for Impacto Vial (PorcentajeObra).

@staticmethod only. Maps Domain Result -> Presentation Schema.
"""
import math
import uuid
from typing import List

from modules.liquidaciones.domain.results.liquidacion_especifico.impacto_vial_primera_revision_result import (
    ImpactoVialPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_impacto_vial_schemas import (
    LiquidacionImpactoVialOutput,
    LiquidacionImpactoVialCotizarOutput,
    LiquidacionImpactoVialCotizarDetalleOut,
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
)
from core.pagination import PaginatedData


class LiquidacionImpactoVialPresenter:
    @staticmethod
    def present_primera_revision(domain_result: ImpactoVialPrimeraRevisionResult) -> LiquidacionImpactoVialOutput:
        general = domain_result.liquidacion_general
        tipo = domain_result.liquidacion_tipo
        especifica = domain_result.liquidacion_especifica

        general_out = LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            municipalidad_id=uuid.UUID(general.municipalidad_id),
            usuario_creador=UsuarioCreadorOutput(id=uuid.UUID(general.usuario_creador.id)),
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            igv_id=uuid.UUID(general.igv_id) if general.igv_id else None,
            uit_id=uuid.UUID(general.uit_id) if general.uit_id else None,
            proyecto=ProyectoOutput(
                id=uuid.UUID(general.proyecto.id),
                denominacion=general.proyecto.denominacion,
                nombre_propietario=general.proyecto.nombre_propietario,
                direccion=general.proyecto.direccion,
                distrito_id=uuid.UUID(general.proyecto.distrito_id),
                entidad=EntidadInlineSchema(
                    tipo_documento=general.proyecto.entidad.tipo_documento,
                    numero_documento=general.proyecto.entidad.numero_documento,
                    razon_social=general.proyecto.entidad.razon_social,
                ) if general.proyecto.entidad else None,
            ),
        )

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

        return LiquidacionImpactoVialOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=tipo_datos_out,
        )

    @staticmethod
    def present_cotizacion(domain_result: CotizacionPorcentajeObraResult) -> LiquidacionImpactoVialCotizarOutput:
        """
        Maps CotizacionPorcentajeObraResult to LiquidacionImpactoVialCotizarOutput.
        """
        return LiquidacionImpactoVialCotizarOutput(
            valor_declarado=domain_result.valor_declarado,
            porcentaje_liquidacion=domain_result.porcentaje_liquidacion,
            derecho_minimo=domain_result.derecho_minimo,
            derecho_maximo=domain_result.derecho_maximo,
            porcentaje_minimo_uit=domain_result.porcentaje_minimo_uit,
            derecho_aplicado_id=uuid.UUID(domain_result.derecho_aplicado_id),
            detalles=[
                LiquidacionImpactoVialCotizarDetalleOut(
                    tarifa_id=uuid.UUID(d.tarifa_id),
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
        liquidaciones: List[ImpactoVialPrimeraRevisionResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionImpactoVialOutput]:
        """
        Maps a list of ImpactoVialPrimeraRevisionResult domain DTOs to PaginatedData[LiquidacionImpactoVialOutput].

        Each item is presented by calling present_primera_revision.
        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionImpactoVialOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionImpactoVialPresenter.present_primera_revision(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(domain_result: ImpactoVialPrimeraRevisionResult) -> LiquidacionImpactoVialOutput:
        """
        Maps a single ImpactoVialPrimeraRevisionResult domain DTO to LiquidacionImpactoVialOutput.
        Delegates to present_primera_revision.
        """
        return LiquidacionImpactoVialPresenter.present_primera_revision(domain_result)
