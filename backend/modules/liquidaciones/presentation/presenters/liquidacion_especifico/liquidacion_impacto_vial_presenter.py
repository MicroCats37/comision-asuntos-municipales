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

    @staticmethod
    def present_tarifas_vigentes(tarifas, especialidades_disponibles) -> dict:
        """
        Maps TarifaPorcentajeObra domain objects and LiquidacionEspecialidadDisponibles
        to a dict response.

        With tarifa-unica-especialidades: the single tariff no longer has an
        especialidad FK. The frontend must use LiquidacionEspecialidadDisponibles
        to let the user pick which specialties to apply.

        Presenter only knows about Domain objects and plain dicts — no ORM access.
        """
        return {
            "tarifas": [
                {
                    "id": str(t.id),
                    "porcentaje_liquidacion": float(t.porcentaje_liquidacion),
                }
                for t in tarifas
            ],
            "especialidades_disponibles": [
                {
                    "id": str(e.especialidad.id),
                    "codigo": e.especialidad.codigo if hasattr(e.especialidad, 'codigo') else None,
                    "nombre": e.especialidad.nombre,
                }
                for e in especialidades_disponibles
            ],
        }
