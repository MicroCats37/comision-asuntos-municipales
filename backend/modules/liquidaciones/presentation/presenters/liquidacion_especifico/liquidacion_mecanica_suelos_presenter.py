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
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
    MunicipalidadOutput,
    IgvOutput,
    UitOutput,
    DistritoOutput,
    ProvinciaOutput,
    DepartamentoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
    LiquidacionPorMetroCuadradoDatosOut,
)
from core.pagination import PaginatedData

from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
    MecanicaSuelosPrimeraRevisionResult,
    LiquidacionEspecificaMecanicaSuelosResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    ProyectoResult,
    EntidadResult,
    UsuarioCreadorResult,
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

        general_out = LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            municipalidad=MunicipalidadOutput(
                id=uuid.UUID(general.municipalidad.id),
                codigo=general.municipalidad.codigo,
                nombre=general.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorOutput(
                id=uuid.UUID(general.usuario_creador.id),
                nombres=general.usuario_creador.nombres,
                apellidos=general.usuario_creador.apellidos,
                email=general.usuario_creador.email,
                dni=general.usuario_creador.dni,
                username=general.usuario_creador.username,
            ),
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            retencion=general.retencion,
            igv=(
                IgvOutput(
                    id=uuid.UUID(general.igv.id),
                    valor=general.igv.valor,
                    periodo_inicio=general.igv.periodo_inicio,
                )
                if general.igv
                else None
            ),
            uit=(
                UitOutput(
                    id=uuid.UUID(general.uit.id),
                    valor=general.uit.valor,
                    periodo_inicio=general.uit.periodo_inicio,
                )
                if general.uit
                else None
            ),
            proyecto=ProyectoOutput(
                id=uuid.UUID(general.proyecto.id),
                denominacion=general.proyecto.denominacion,
                nombre_propietario=general.proyecto.nombre_propietario,
                direccion=general.proyecto.direccion,
                distrito=(
                    DistritoOutput(
                        id=uuid.UUID(general.proyecto.distrito.id),
                        nombre=general.proyecto.distrito.nombre,
                        ubigeo=general.proyecto.distrito.ubigeo,
                        provincia=(
                            ProvinciaOutput(
                                id=uuid.UUID(general.proyecto.distrito.provincia.id),
                                nombre=general.proyecto.distrito.provincia.nombre,
                            )
                            if general.proyecto.distrito.provincia
                            else None
                        ),
                        departamento=(
                            DepartamentoOutput(
                                id=uuid.UUID(general.proyecto.distrito.departamento.id),
                                nombre=general.proyecto.distrito.departamento.nombre,
                            )
                            if general.proyecto.distrito.departamento
                            else None
                        ),
                    )
                    if general.proyecto.distrito
                    else None
                ),
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

        especifica_out = LiquidacionPorMetroCuadradoDatosOut(
            id=uuid.UUID(tipo.id),
            area_m2=tipo.area_m2,
            costo_por_m2=tipo.costo_por_m2,
            derecho_minimo=tipo.derecho_minimo,
            derecho_maximo=tipo.derecho_maximo or 0.0,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id),
            derecho_aplicado_id=uuid.UUID(tipo.derecho_aplicado_id),
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
