"""
LiquidacionGeneralOrchestrator — sync facade for general liquidacion listing.

Thin sync facade. Validates input and delegates to Core for ORM operations.
"""
import math
from typing import List
from injector import inject

from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
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
from core.pagination import PaginatedData


class LiquidacionGeneralOrchestrator:
    """
    Sync facade for general liquidacion listing.

    Responsibilities:
    - Input validation (pagination boundaries)
    - Delegates to Core service for ORM operations
    - Maps ORM objects to domain Results
    """

    @inject
    def __init__(
        self,
        general_core_service: LiquidacionGeneralCoreService,
    ):
        self.general_core_service = general_core_service

    def listar_liquidaciones_generales(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
    ) -> tuple[List[LiquidacionGeneralResult], int]:
        """
        Returns paginated LiquidacionGeneralResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionGeneralResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_generales_paginated(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
        )

        # Build LiquidacionGeneralResult domain DTOs from ORM objects
        domain_results: List[LiquidacionGeneralResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_general_result(lg))

        return domain_results, total

    def _build_general_result(self, lg) -> LiquidacionGeneralResult:
        """
        Maps a LiquidacionGeneral ORM object to LiquidacionGeneralResult domain DTO.
        """
        proyecto = lg.proyecto

        # La razon social/tipo/numero viven DENORMALIZADOS en Proyecto
        ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
        ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
        ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None

        # Build distrito objeto (con provincia/departamento)
        distrito_result = None
        if getattr(proyecto, "distrito_id", None):
            distrito = proyecto.distrito
            if distrito:
                distrito_result = DistritoResult(
                    id=str(distrito.id),
                    nombre=distrito.nombre,
                    ubigeo=getattr(distrito, "ubigeo", None),
                    provincia=(
                        ProvinciaResult(
                            id=str(distrito.provincia.id),
                            nombre=distrito.provincia.nombre,
                        )
                        if distrito.provincia
                        else None
                    ),
                    departamento=(
                        DepartamentoResult(
                            id=str(distrito.provincia.departamento.id),
                            nombre=distrito.provincia.departamento.nombre,
                        )
                        if distrito.provincia and distrito.provincia.departamento
                        else None
                    ),
                )

        # Build contacto
        contacto_result = None
        if lg.contacto:
            contacto_result = ContactoResult(
                id=str(lg.contacto.id),
                nombres=getattr(lg.contacto, 'nombres', None),
                apellidos=getattr(lg.contacto, 'apellidos', None),
                dni=getattr(lg.contacto, 'dni', None),
                cargo=getattr(lg.contacto, 'cargo', None),
                telefono=getattr(lg.contacto, 'telefono', None),
                celular=getattr(lg.contacto, 'celular', None),
                email=getattr(lg.contacto, 'email', None),
            )

        # Build revisions previas
        revisiones_previas = self.general_core_service.build_revisiones_previas_result(lg)

        # Build delegados (FK adjunta liquidacion_delegados)
        delegados = self.general_core_service.build_delegados_result(lg)

        return LiquidacionGeneralResult(
            id=str(lg.id),
            municipalidad=MunicipalidadResult(
                id=str(lg.municipalidad.id),
                codigo=lg.municipalidad.codigo,
                nombre=lg.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(lg.usuario_creador.id) if lg.usuario_creador else "00000000-0000-0000-0000-000000000000",
                nombres=getattr(lg.usuario_creador, "nombres", None),
                apellidos=getattr(lg.usuario_creador, "apellidos", None),
                email=getattr(lg.usuario_creador, "email", None),
                dni=getattr(lg.usuario_creador, "dni", None),
                username=getattr(lg.usuario_creador, "username", None),
            ),
            fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
            expediente=lg.expediente or "",
            observacion=lg.observacion,
            numero_revision=lg.numero_revision,
            sub_total=float(lg.sub_total) if lg.sub_total else 0.0,
            total=float(lg.total) if lg.total else 0.0,
            retencion=lg.retencion,
            igv=(
                IgvResult(
                    id=str(lg.igv_id.id),
                    valor=float(lg.igv_id.valor),
                    periodo_inicio=lg.igv_id.periodo_inicio.isoformat() if lg.igv_id.periodo_inicio else None,
                )
                if lg.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(lg.uit_id.id),
                    valor=float(lg.uit_id.valor),
                    periodo_inicio=lg.uit_id.periodo_inicio.isoformat() if lg.uit_id.periodo_inicio else None,
                )
                if lg.uit_id
                else None
            ),
            proyecto=ProyectoResult(
                id=str(proyecto.id),
                denominacion=proyecto.denominacion,
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito=distrito_result,
                # Denormalized entity fields (safe access via getattr)
                entidad_tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None),
                entidad_numero_documento=getattr(proyecto, 'entidad_numero_documento', None),
                entidad_razon_social=getattr(proyecto, 'entidad_razon_social', None),
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
            contacto=contacto_result,
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=lg.tipo_liquidacion.codigo,
                    nombre=lg.tipo_liquidacion.nombre,
                )
                if lg.tipo_liquidacion
                else None
            ),
            revisiones_previas=revisiones_previas,
            delegados=delegados,
        )

    def listar_ultimas_liquidaciones_generales(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        numero=None,
    ) -> tuple[List[LiquidacionGeneralResult], int]:
        """
        Returns paginated LiquidacionGeneralResult list containing only the latest revision
        per (proyecto, tipo_liquidacion) pair.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionGeneralResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_ultimas_generales_paginated(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
            numero=numero,
        )

        # Build LiquidacionGeneralResult domain DTOs from ORM objects
        domain_results: List[LiquidacionGeneralResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_general_result(lg))

        return domain_results, total
