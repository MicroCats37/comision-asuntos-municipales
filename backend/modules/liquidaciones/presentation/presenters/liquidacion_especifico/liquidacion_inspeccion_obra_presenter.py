"""
Presenter de Inspección de Obra.
Mapea el Result del Dominio al Schema final de Presentación.
"""
import math
import uuid
from typing import List

from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
    LiquidacionEspecificaInspeccionObraResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    UsuarioCreadorResult,
    ProyectoResult,
    EntidadResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
    LiquidacionVisitasResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
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
        """Assembles the final Inspeccion Obra output from the Result."""
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
            igv_id=uuid.UUID(general.igv_id) if general.igv_id else uuid.uuid4(),
            uit_id=uuid.UUID(general.uit_id) if general.uit_id else uuid.uuid4(),
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
        liquidaciones: List,
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionInspeccionObraOutput]:
        """
        Maps a list of LiquidacionGeneral ORM objects to PaginatedData[LiquidacionInspeccionObraOutput].

        Each item is presented by calling present_primera_revision internally,
        building an InspeccionObraPrimeraRevisionResult from the ORM object.
        """
        items: List[LiquidacionInspeccionObraOutput] = []
        for lg in liquidaciones:
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

            # Get inspeccion_obra (OneToOne from LiquidacionGeneral - identity wrapper)
            io = lg.inspeccion_obra

            # Build LiquidacionEspecificaInspeccionObraResult (identity wrapper)
            especifica_result = LiquidacionEspecificaInspeccionObraResult(
                id=str(io.id),
                numero=io.numero,
            )

            # Build LiquidacionVisitasResult from prefetched liquidacion_visitas
            # Note: liquidacion_visitas is a ForeignKey (not OneToOne), so we access via .first()
            lv = lg.liquidacion_visitas.first()
            if lv is None:
                continue
            tipo_result = LiquidacionVisitasResult(
                id=str(lv.id),
                cantidad_visitas=lv.cantidad_visitas,
                porcentaje_uit=float(lv.porcentaje_uit) if lv.porcentaje_uit else 0.0,
                categoria=lv.categoria or "",
                tarifa_aplicada_id=str(lv.tarifa_aplicada_id),
            )

            domain_result = InspeccionObraPrimeraRevisionResult(
                liquidacion_general=general_result,
                liquidacion_especifica=especifica_result,
                liquidacion_tipo=tipo_result,
            )

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
    def present_detalle(lg) -> LiquidacionInspeccionObraOutput:
        """
        Maps a single LiquidacionGeneral ORM object to LiquidacionInspeccionObraOutput.

        Uses the same prefetch chain as present_list but for a single object.
        """
        # Build LiquidacionGeneralResult from ORM
        proyecto = lg.proyecto
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # When entidad FK is None, use denormalized fields from proyecto
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

        # Get inspeccion_obra (OneToOne from LiquidacionGeneral - identity wrapper)
        io = lg.inspeccion_obra

        # Build LiquidacionEspecificaInspeccionObraResult (identity wrapper)
        especifica_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(io.id),
            numero=io.numero,
        )

        # Build LiquidacionVisitasResult from prefetched liquidacion_visitas
        lv = lg.liquidacion_visitas.first()
        tipo_result = LiquidacionVisitasResult(
            id=str(lv.id),
            cantidad_visitas=lv.cantidad_visitas,
            porcentaje_uit=float(lv.porcentaje_uit) if lv.porcentaje_uit else 0.0,
            categoria=lv.categoria or "",
            tarifa_aplicada_id=str(lv.tarifa_aplicada_id),
        )

        domain_result = InspeccionObraPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

        return LiquidacionInspeccionObraPresenter.present_primera_revision(domain_result)
