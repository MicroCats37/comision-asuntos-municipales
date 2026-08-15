"""
Presenter de Inspección de Obra.
Mapea el Result del Dominio al Schema final de Presentación.

@staticmethod only. Sin acceso a ORM.
"""
import math
import uuid
from typing import List

from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
    ContactoOutput,
    MunicipalidadOutput,
    IgvOutput,
    UitOutput,
    DistritoOutput,
    ProvinciaOutput,
    DepartamentoOutput,
    TipoLiquidacionOutput,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    LiquidacionDelegadoOut,
    EspecialidadRevisionOut,
    LiquidacionDelegadoDelegadoOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasDatosOut,
)
from core.pagination import PaginatedData


class LiquidacionInspeccionObraPresenter:
    @staticmethod
    def present_primera_revision(
        result: InspeccionObraPrimeraRevisionResult,
    ) -> LiquidacionInspeccionObraOutput:
        """Assembles the final Inspeccion Obra output from the Domain Result."""
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
            tipo_liquidacion=(
                TipoLiquidacionOutput(
                    codigo=general.tipo_liquidacion.codigo,
                    nombre=general.tipo_liquidacion.nombre,
                )
                if general.tipo_liquidacion
                else None
            ),
            delegados=[
                LiquidacionDelegadoOut(
                    id=uuid.UUID(d.id),
                    liquidacion_id=uuid.UUID(d.liquidacion_id),
                    delegado_id=uuid.UUID(d.delegado_id),
                    especialidad_revision=EspecialidadRevisionOut(
                        id=uuid.UUID(d.especialidad_revision_id),
                        nombre=d.especialidad_revision_nombre,
                    ),
                    delegado=LiquidacionDelegadoDelegadoOut(
                        id=uuid.UUID(d.delegado_id),
                        cip=d.delegado_cip,
                        dni=d.delegado_dni,
                        nombre_completo=d.delegado_nombre_completo,
                    ),
                    periodo=d.periodo,
                    dictamen_revision=d.dictamen_revision,
                    fecha_presentacion=d.fecha_presentacion,
                    fecha_revision=d.fecha_revision,
                )
                for d in (general.delegados or [])
            ],
        )

        tipo_out = LiquidacionTipoOutput(
            id=uuid.UUID(especifica.id),
            numero=especifica.numero,
        )

        especifica_out = LiquidacionPorCategoriaVisitasDatosOut(
            id=uuid.UUID(tipo.id),
            cantidad_visitas=tipo.cantidad_visitas,
            porcentaje_uit=tipo.porcentaje_uit,
            categoria=tipo.categoria,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id),
        )

        return LiquidacionInspeccionObraOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=especifica_out,
        )

    @staticmethod
    def present_list(
        liquidaciones: List[InspeccionObraPrimeraRevisionResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionInspeccionObraOutput]:
        """
        Maps a list of InspeccionObraPrimeraRevisionResult domain DTOs to PaginatedData[LiquidacionInspeccionObraOutput].

        Each item is presented by calling present_primera_revision.
        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionInspeccionObraOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionInspeccionObraPresenter.present_primera_revision(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(domain_result: InspeccionObraPrimeraRevisionResult) -> LiquidacionInspeccionObraOutput:
        """
        Maps a single InspeccionObraPrimeraRevisionResult domain DTO to LiquidacionInspeccionObraOutput.
        Delegates to present_primera_revision.
        """
        return LiquidacionInspeccionObraPresenter.present_primera_revision(domain_result)
