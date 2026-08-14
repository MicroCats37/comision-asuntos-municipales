"""
LiquidacionGeneralPresenter — Maps Domain Results to API Schema Out.

NO ORM. Only @staticmethod. Only maps Result → Schema Out.
"""
import math
import uuid
from typing import List

from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    EntidadResult,
    ProyectoResult,
    UsuarioCreadorResult,
    MunicipalidadResult,
    IgvResult,
    UitResult,
    DistritoResult,
    ProvinciaResult,
    DepartamentoResult,
    TipoLiquidacionResult,
    LiquidacionPreviaResult,
    ContactoResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    EntidadInlineSchema,
    ProyectoOutput,
    UsuarioCreadorOutput,
    MunicipalidadOutput,
    IgvOutput,
    UitOutput,
    DistritoOutput,
    ProvinciaOutput,
    DepartamentoOutput,
    TipoLiquidacionOutput,
    LiquidacionPreviaOutput,
    ContactoOutput,
)
from core.pagination import PaginatedData


class LiquidacionGeneralPresenter:
    """
    Presenter for general Liquidacion endpoints.
    Maps LiquidacionGeneralResult to LiquidacionGeneralOutput. Zero ORM.
    """

    @staticmethod
    def _map_result_to_output(result: LiquidacionGeneralResult) -> LiquidacionGeneralOutput:
        """Maps a single LiquidacionGeneralResult to LiquidacionGeneralOutput."""
        general = result

        # Build distrito output
        distrito_out = None
        if general.proyecto.distrito:
            d = general.proyecto.distrito
            provincia_out = None
            if d.provincia:
                provincia_out = ProvinciaOutput(
                    id=uuid.UUID(d.provincia.id),
                    nombre=d.provincia.nombre,
                )
                if d.provincia.departamento:
                    provincia_out.departamento = DepartamentoOutput(
                        id=uuid.UUID(d.provincia.departamento.id),
                        nombre=d.provincia.departamento.nombre,
                    )
            distrito_out = DistritoOutput(
                id=uuid.UUID(d.id),
                nombre=d.nombre,
                ubigeo=d.ubigeo,
                provincia=provincia_out,
            )

        # Build entidad output using denormalized proyecto.entidad_* fields (safe getattr)
        # Pattern: use getattr with None default, then create schema only if value exists
        ent_tipo = getattr(general.proyecto, 'entidad_tipo_documento', None)
        ent_numero = getattr(general.proyecto, 'entidad_numero_documento', None)
        ent_razon = getattr(general.proyecto, 'entidad_razon_social', None)
        entidad_out = None
        if ent_tipo or ent_numero or ent_razon:
            entidad_out = EntidadInlineSchema(
                tipo_documento=ent_tipo or "",
                numero_documento=ent_numero or "",
                razon_social=ent_razon or "",
            )

        # Build proyecto output
        proyecto_out = ProyectoOutput(
            id=uuid.UUID(general.proyecto.id),
            denominacion=general.proyecto.denominacion,
            nombre_propietario=general.proyecto.nombre_propietario,
            direccion=general.proyecto.direccion,
            distrito=distrito_out,
            entidad=entidad_out,
        )

        # Build municipalidad output
        municipalidad_out = MunicipalidadOutput(
            id=uuid.UUID(general.municipalidad.id),
            codigo=general.municipalidad.codigo,
            nombre=general.municipalidad.nombre,
        )

        # Build usuario_creador output
        usuario_out = UsuarioCreadorOutput(
            id=uuid.UUID(general.usuario_creador.id) if general.usuario_creador.id != "00000000-0000-0000-0000-000000000000" else uuid.UUID("00000000-0000-0000-0000-000000000000"),
            nombres=general.usuario_creador.nombres,
            apellidos=general.usuario_creador.apellidos,
            email=general.usuario_creador.email,
            dni=general.usuario_creador.dni,
            username=general.usuario_creador.username,
        )

        # Build igv output
        igv_out = None
        if general.igv:
            igv_out = IgvOutput(
                id=uuid.UUID(general.igv.id),
                valor=general.igv.valor,
                periodo_inicio=general.igv.periodo_inicio,
            )

        # Build uit output
        uit_out = None
        if general.uit:
            uit_out = UitOutput(
                id=uuid.UUID(general.uit.id),
                valor=general.uit.valor,
                periodo_inicio=general.uit.periodo_inicio,
            )

        # Build tipo_liquidacion output
        tipo_liq_out = None
        if general.tipo_liquidacion:
            tipo_liq_out = TipoLiquidacionOutput(
                codigo=general.tipo_liquidacion.codigo,
                nombre=general.tipo_liquidacion.nombre,
            )

        # Build contacto output
        contacto_out = None
        if general.contacto:
            contacto_out = ContactoOutput(
                id=uuid.UUID(general.contacto.id),
                nombres=general.contacto.nombres,
                apellidos=general.contacto.apellidos,
                dni=general.contacto.dni,
                cargo=general.contacto.cargo,
                telefono=general.contacto.telefono,
                celular=general.contacto.celular,
                email=general.contacto.email,
            )

        # Build revisiones previas output
        previas_out: List[LiquidacionPreviaOutput] = []
        for prev in general.revisiones_previas:
            previas_out.append(LiquidacionPreviaOutput(
                id=uuid.UUID(prev.id),
                numero_revision=prev.numero_revision,
                expediente=prev.expediente,
            ))

        return LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            municipalidad=municipalidad_out,
            usuario_creador=usuario_out,
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            retencion=general.retencion,
            igv=igv_out,
            uit=uit_out,
            proyecto=proyecto_out,
            contacto=contacto_out,
            tipo_liquidacion=tipo_liq_out,
            revisiones_previas=previas_out,
        )

    @staticmethod
    def present_list(
        liquidaciones: List[LiquidacionGeneralResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionGeneralOutput]:
        """
        Maps a list of LiquidacionGeneralResult domain DTOs to PaginatedData[LiquidacionGeneralOutput].

        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionGeneralOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionGeneralPresenter._map_result_to_output(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
