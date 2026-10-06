"""
LiquidacionGeneralPresenter — Maps Domain Results to API Schema Out.

NO ORM. Only @staticmethod. Only maps Result → Schema Out.
"""
import math
import uuid
from typing import List, Optional

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
    ContactoResult,
    LiquidacionDelegadoEnGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_comprobante_result import (
    LiquidacionComprobanteResult,
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
    ContactoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.comprobante_schemas import (
    LiquidacionComprobanteOutput,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_schemas import (
    DelegadoBaseOut,
    EspecialidadRevisionMinimalOut,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    LiquidacionDelegadoDatosOut,
    LiquidacionDelegadoEnGeneralOut,
)
from core.pagination import PaginatedData


class LiquidacionGeneralPresenter:
    """
    Presenter for general Liquidacion endpoints.
    Maps LiquidacionGeneralResult to LiquidacionGeneralOutput. Zero ORM.

    codigo_cta is pre-resolved at the service layer and passed in LiquidacionGeneralResult.
    """

    @staticmethod
    def _map_comprobante(result: Optional[LiquidacionComprobanteResult]) -> Optional[LiquidacionComprobanteOutput]:
        """Maps a LiquidacionComprobanteResult to LiquidacionComprobanteOutput."""
        if not result:
            return None
        return LiquidacionComprobanteOutput(
            id=uuid.UUID(result.id),
            tipo_comprobante=result.tipo_comprobante,
            serie=result.serie,
            numero=result.numero,
            fecha_emision=result.fecha_emision,
            monto=result.monto,
            activo=result.activo,
            motivo_reemplazo=result.motivo_reemplazo,
        )

    @staticmethod
    def _map_comprobantes(results: list[LiquidacionComprobanteResult]) -> list[LiquidacionComprobanteOutput]:
        """Maps a list of LiquidacionComprobanteResult to a list of LiquidacionComprobanteOutput."""
        return [LiquidacionGeneralPresenter._map_comprobante(r) for r in results]

    @staticmethod
    def _map_result_to_output(result: LiquidacionGeneralResult) -> LiquidacionGeneralOutput:
        """Maps a single LiquidacionGeneralResult to LiquidacionGeneralOutput."""
        general = result

        # Build distrito output
        distrito_out = None
        if general.proyecto and general.proyecto.distrito:
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
            nombre_propietario=general.proyecto.nombre_propietario,
            direccion=general.proyecto.direccion,
            urbanizacion=getattr(general.proyecto, 'urbanizacion', None),
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
        usuario_out = None
        if general.usuario_creador:
            usuario_out = UsuarioCreadorOutput(
                id=uuid.UUID(general.usuario_creador.id),
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

        # Build comprobantes list output
        comprobantes_out = LiquidacionGeneralPresenter._map_comprobantes(general.comprobantes)

        return LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            estado=general.estado,
            municipalidad=municipalidad_out,
            usuario_creador=usuario_out,
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            retencion=general.retencion,
            legacy=general.legacy,
            codigo_cta=general.codigo_cta,
            igv=igv_out,
            uit=uit_out,
            proyecto=proyecto_out,
            contacto=contacto_out,
            tipo_liquidacion=tipo_liq_out,
            comprobantes=comprobantes_out,
            denominacion_de_proyecto=general.denominacion_de_proyecto,
            eliminado=general.eliminado,
            fecha_eliminacion=general.fecha_eliminacion,
            motivo_eliminacion=general.motivo_eliminacion,
            modo_calculo=general.modo_calculo,
        )

    @staticmethod
    def _map_delegados(general: LiquidacionGeneralResult) -> List[LiquidacionDelegadoEnGeneralOut]:
        """
        Maps the 'delegados' flat-join fields from LiquidacionGeneralResult
        into a list of LiquidacionDelegadoEnGeneralOut ({ datos, delegado }).
        Returns [] if general.delegados is empty or None.
        """
        return [
            LiquidacionDelegadoEnGeneralOut(
                datos=LiquidacionDelegadoDatosOut(
                    periodo=d.periodo,
                    mes=d.mes,
                    dictamen_revision=d.dictamen_revision,
                    fecha_presentacion=d.fecha_presentacion,
                    fecha_revision=d.fecha_revision,
                ),
                delegado=DelegadoBaseOut(
                    id=uuid.UUID(d.delegado_id),
                    nombre_completo=d.delegado_nombre_completo,
                    cip=d.delegado_cip,
                    tipo=d.tipo or "",
                    especialidad=EspecialidadRevisionMinimalOut(
                        id=uuid.UUID(d.especialidad_revision_id),
                        nombre=d.especialidad_revision_nombre,
                    ) if d.especialidad_revision_id else None,
                ),
            )
            for d in (general.delegados or [])
        ]

    @staticmethod
    def present_liquidacion_general(general: LiquidacionGeneralResult) -> LiquidacionGeneralOutput:
        """
        Maps a LiquidacionGeneralResult to LiquidacionGeneralOutput.
        Used by the 6 specific presenters to avoid duplicating the general mapping block.
        """
        # Build distrito output (with provincia and departamento as sibling fields)
        distrito_out = None
        if general.proyecto and general.proyecto.distrito:
            d = general.proyecto.distrito
            provincia_out = None
            if d.provincia:
                provincia_out = ProvinciaOutput(
                    id=uuid.UUID(d.provincia.id),
                    nombre=d.provincia.nombre,
                )
            departamento_out = None
            if d.departamento:
                departamento_out = DepartamentoOutput(
                    id=uuid.UUID(d.departamento.id),
                    nombre=d.departamento.nombre,
                )
            distrito_out = DistritoOutput(
                id=uuid.UUID(d.id),
                nombre=d.nombre,
                ubigeo=d.ubigeo,
                provincia=provincia_out,
                departamento=departamento_out,
            )

        # Build entidad output (supports both denormalized fields and nested entidad object)
        entidad_out = None
        ent_tipo = getattr(general.proyecto, 'entidad_tipo_documento', None) or (
            general.proyecto.entidad.tipo_documento if general.proyecto.entidad else None
        )
        ent_numero = getattr(general.proyecto, 'entidad_numero_documento', None) or (
            general.proyecto.entidad.numero_documento if general.proyecto.entidad else None
        )
        ent_razon = getattr(general.proyecto, 'entidad_razon_social', None) or (
            general.proyecto.entidad.razon_social if general.proyecto.entidad else None
        )
        if ent_tipo or ent_numero or ent_razon:
            entidad_out = EntidadInlineSchema(
                tipo_documento=ent_tipo or "",
                numero_documento=ent_numero or "",
                razon_social=ent_razon or "",
            )

        # Build proyecto output
        proyecto_out = ProyectoOutput(
            id=uuid.UUID(general.proyecto.id),
            nombre_propietario=general.proyecto.nombre_propietario,
            direccion=general.proyecto.direccion,
            urbanizacion=getattr(general.proyecto, 'urbanizacion', None),
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
        usuario_out = None
        if general.usuario_creador:
            usuario_out = UsuarioCreadorOutput(
                id=uuid.UUID(general.usuario_creador.id),
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

        # Build comprobantes list output
        comprobantes_out = LiquidacionGeneralPresenter._map_comprobantes(general.comprobantes)

        return LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            estado=general.estado,
            municipalidad=municipalidad_out,
            usuario_creador=usuario_out,
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            retencion=general.retencion,
            legacy=general.legacy,
            codigo_cta=general.codigo_cta,
            igv=igv_out,
            uit=uit_out,
            proyecto=proyecto_out,
            contacto=contacto_out,
            tipo_liquidacion=tipo_liq_out,
            delegados=LiquidacionGeneralPresenter._map_delegados(general),
            comprobantes=comprobantes_out,
            denominacion_de_proyecto=general.denominacion_de_proyecto,
            eliminado=general.eliminado,
            fecha_eliminacion=general.fecha_eliminacion,
            motivo_eliminacion=general.motivo_eliminacion,
            modo_calculo=general.modo_calculo,
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
            items.append(LiquidacionGeneralPresenter.present_liquidacion_general(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
