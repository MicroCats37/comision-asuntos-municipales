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
        liquidaciones: List,
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionMecanicaSuelosOutput]:
        """
        Maps a list of LiquidacionGeneral ORM objects to PaginatedData[LiquidacionMecanicaSuelosOutput].

        Each item is presented by calling present_detalle internally.
        """
        items: List[LiquidacionMecanicaSuelosOutput] = []
        for lg in liquidaciones:
            items.append(LiquidacionMecanicaSuelosPresenter.present_detalle(lg))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(lg) -> LiquidacionMecanicaSuelosOutput:
        """
        Maps a single LiquidacionGeneral ORM object to LiquidacionMecanicaSuelosOutput.

        Uses the same mapping logic as present_list's internal loop.
        """
        # Build LiquidacionGeneralResult from ORM
        proyecto = lg.proyecto
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # When entidad FK is None, use denormalized fields from proyecto
        # (these are populated when entity is created inline)
        if entidad is None:
            ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
            ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
            ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None
        else:
            ent_tipo = entidad.tipo_documento
            ent_numero = entidad.numero_documento
            ent_razon = entidad.razon_social

        general_result = LiquidacionGeneralResult(
            id=str(lg.id),
            municipalidad_id=str(lg.municipalidad_id),
            usuario_creador=UsuarioCreadorResult(
                id=str(lg.usuario_creador.id) if lg.usuario_creador else "00000000-0000-0000-0000-000000000000",
            ),
            fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
            expediente=lg.expediente or "",
            observacion=lg.observacion,
            numero_revision=lg.numero_revision,
            sub_total=float(lg.sub_total) if lg.sub_total else 0.0,
            total=float(lg.total) if lg.total else 0.0,
            igv_id=str(lg.igv_id.id) if lg.igv_id else None,
            uit_id=str(lg.uit_id.id) if lg.uit_id else None,
            proyecto=ProyectoResult(
                id=str(proyecto.id),
                denominacion=proyecto.denominacion,
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito_id=str(proyecto.distrito_id),
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
        )

        # Get MS specific data (OneToOne from LiquidacionGeneral)
        mecanica_suelos = lg.mecanica_suelos
        m2 = lg.liquidacion_m2.all()[0] if lg.liquidacion_m2.exists() else None

        # Build LiquidacionEspecificaMecanicaSuelosResult
        especifica_result = LiquidacionEspecificaMecanicaSuelosResult(
            id=str(mecanica_suelos.id),
            numero=mecanica_suelos.numero,
        )

        # Build LiquidacionM2Result from prefetched liquidacion_m2
        tipo_result = LiquidacionM2Result(
            id=str(m2.id),
            area_m2=float(m2.area_m2) if m2.area_m2 else 0.0,
            costo_por_m2=float(m2.costo_por_m2) if m2.costo_por_m2 else 0.0,
            derecho_minimo=float(m2.derecho_minimo) if m2.derecho_minimo else 0.0,
            derecho_maximo=float(m2.derecho_maximo) if m2.derecho_maximo else None,
            derecho_aplicado_id=str(m2.derecho.id) if m2.derecho else "",
            tarifa_aplicada_id=str(m2.tarifa_aplicada.id) if m2.tarifa_aplicada else "",
        )

        domain_result = MecanicaSuelosPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

        return LiquidacionMecanicaSuelosPresenter.present_primera_revision(domain_result)
