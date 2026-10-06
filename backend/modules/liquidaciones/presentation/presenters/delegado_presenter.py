"""
DelegadoPresenter — Maps Domain Results to API Schema Out.

NO ORM. Only @staticmethod. Only maps Result → Schema Out.
"""
import uuid
import math
from typing import List

from modules.liquidaciones.domain.results.delegado.delegado_result import (
    PerfilIngenieroResult,
    DelegadoResult,
    DelegadoListResult,
    MunicipalidadesAsignadasResult,
    DelegadoMunicipalidadesResult,
    DelegadoForMunicipalidadResult,
    DelegadosPorMunicipalidadResult,
    EspecialidadRevisionResult,
    DelegadoVigenteResult,
    DelegadosVigentesResult,
    LiquidacionDelegadoResult,
    LiquidacionDelegadoBatchResult,
    LiquidacionDelegadoLiquidacionMinimal,
    LiquidacionDelegadoDelegadoMinimal,
    TipoLiquidacionMinimalResult,
    DelegadoCandidatasResult,
    EspecialidadesRevisionResult,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_schemas import (
    PerfilIngenieroOut,
    DelegadoOut,
    DelegadoListOut,
    MunicipalidadesAsignadasOut,
    DelegadoMunicipalidadesOut,
    DelegadoForMunicipalidadOut,
    EspecialidadOut,
    CapituloOut,
    MunicipalidadBasicOut,
    DelegadoBaseOut,
    EspecialidadRevisionMinimalOut,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    EspecialidadRevisionOut,
    EspecialidadesRevisionOut,
    EspecialidadRevisionOpcionOut,
    DelegadoVigenteOut,
    DelegadosVigentesOut,
    LiquidacionDelegadoOut,
    LiquidacionDelegadoBatchOut,
    DelegadoOperatividadesVigentesOut,
    DelegadoOperacionVigenteOut,
)
from core.pagination import PaginatedData


class DelegadoPresenter:
    """
    Presenter for Delegado endpoints.
    Maps Domain Results to Schema Out. Zero ORM.
    """

    @staticmethod
    def _map_perfil_ingeniero(result: PerfilIngenieroResult) -> PerfilIngenieroOut:
        """Maps PerfilIngenieroResult to PerfilIngenieroOut."""
        return PerfilIngenieroOut(
            id=uuid.UUID(result.id),
            cip=result.cip,
            dni=result.dni,
            nombres=result.nombres,
            apellido_paterno=result.apellido_paterno,
            apellido_materno=result.apellido_materno,
            nombre_completo=result.nombre_completo,
            correo_personal=result.correo_personal,
            correo_institucional=result.correo_institucional,
            especialidad=(
                EspecialidadOut(
                    id=uuid.UUID(result.especialidad.id),
                    codigo=result.especialidad.codigo,
                    nombre=result.especialidad.nombre,
                )
                if result.especialidad
                else None
            ),
            capitulo=(
                CapituloOut(
                    id=uuid.UUID(result.capitulo.id),
                    registro_id=result.capitulo.registro_id,
                    abreviacion=result.capitulo.abreviacion,
                    nombre=result.capitulo.nombre,
                )
                if result.capitulo
                else None
            ),
        )

    @staticmethod
    def _map_municipalidad_asignada(result) -> MunicipalidadesAsignadasOut:
        """Maps MunicipalidadesAsignadasResult to MunicipalidadesAsignadasOut."""
        return MunicipalidadesAsignadasOut(
            id=uuid.UUID(result.id),
            municipalidad=MunicipalidadBasicOut(
                id=uuid.UUID(result.municipalidad.id),
                codigo=result.municipalidad.codigo,
                nombre=result.municipalidad.nombre,
            ),
            tipo=result.tipo,
            periodo_inicio=result.periodo_inicio.isoformat() if result.periodo_inicio else None,
            periodo_fin=result.periodo_fin.isoformat() if result.periodo_fin else None,
            es_vigente=result.es_vigente,
        )

    @staticmethod
    def _map_delegado(result: DelegadoResult) -> DelegadoOut:
        """Maps DelegadoResult to DelegadoOut."""
        return DelegadoOut(
            id=uuid.UUID(result.id),
            perfil_ingeniero=DelegadoPresenter._map_perfil_ingeniero(result.perfil_ingeniero),
            municipalidades=[
                DelegadoPresenter._map_municipalidad_asignada(m)
                for m in result.municipalidades
            ],
            estado=result.estado,
        )

    @staticmethod
    def present_list(domain_result: DelegadoListResult) -> PaginatedData[DelegadoOut]:
        """
        Maps DelegadoListResult to PaginatedData[DelegadoOut].
        """
        items: List[DelegadoOut] = [
            DelegadoPresenter._map_delegado(item)
            for item in domain_result.items
        ]
        return PaginatedData(
            items=items,
            total=domain_result.total,
            page=domain_result.page,
            page_size=domain_result.page_size,
            total_pages=domain_result.total_pages,
        )

    @staticmethod
    def present_municipalidades(domain_result: DelegadoMunicipalidadesResult) -> DelegadoMunicipalidadesOut:
        """
        Maps DelegadoMunicipalidadesResult to DelegadoMunicipalidadesOut.
        """
        return DelegadoMunicipalidadesOut(
            delegado_id=uuid.UUID(domain_result.delegado_id),
            perfil_ingeniero=DelegadoPresenter._map_perfil_ingeniero(domain_result.perfil_ingeniero),
            municipalidades=[
                DelegadoPresenter._map_municipalidad_asignada(m)
                for m in domain_result.municipalidades
            ],
          )

    @staticmethod
    def present_delegados_por_municipalidad(
        domain_result: DelegadosPorMunicipalidadResult,
    ) -> PaginatedData[DelegadoForMunicipalidadOut]:
        """
        Maps DelegadosPorMunicipalidadResult to PaginatedData[DelegadoForMunicipalidadOut].
        """
        items: List[DelegadoForMunicipalidadOut] = [
            DelegadoForMunicipalidadOut(
                id=uuid.UUID(item.id),
                perfil_ingeniero=DelegadoPresenter._map_perfil_ingeniero(item.perfil_ingeniero),
                tipo=item.tipo,
                periodo_inicio=item.periodo_inicio.isoformat() if item.periodo_inicio else None,
                periodo_fin=item.periodo_fin.isoformat() if item.periodo_fin else None,
                es_vigente=item.es_vigente,
            )
            for item in domain_result.items
        ]
        return PaginatedData(
            items=items,
            total=domain_result.total,
            page=domain_result.page,
            page_size=domain_result.page_size,
            total_pages=domain_result.total_pages,
        )

    @staticmethod
    def _map_especialidad_revision(
        result: EspecialidadRevisionResult,
    ) -> EspecialidadRevisionOut:
        """Maps EspecialidadRevisionResult to EspecialidadRevisionOut."""
        return EspecialidadRevisionOut(
            id=uuid.UUID(result.id),
            nombre=result.nombre,
        )

    @staticmethod
    def _map_especialidad_revision_minimal(
        result: EspecialidadRevisionResult,
    ) -> EspecialidadRevisionMinimalOut:
        """Maps EspecialidadRevisionResult to EspecialidadRevisionMinimalOut."""
        return EspecialidadRevisionMinimalOut(
            id=uuid.UUID(result.id),
            nombre=result.nombre,
        )

    @staticmethod
    def _map_delegado_base(result: DelegadoVigenteResult) -> DelegadoBaseOut:
        """
        Maps DelegadoVigenteResult to DelegadoBaseOut.
        Canonical shared helper for building the base delegado shape used across
        LiquidacionGeneralOutput.delegados and other endpoints.
        """
        return DelegadoBaseOut(
            id=uuid.UUID(result.id),
            nombre_completo=result.nombre_completo,
            cip=result.cip,
            tipo=result.tipo,
            especialidad=DelegadoPresenter._map_especialidad_revision_minimal(
                result.especialidad
            ),
        )

    @staticmethod
    def _map_delegado_vigente(result: DelegadoVigenteResult) -> DelegadoVigenteOut:
        """Maps DelegadoVigenteResult to DelegadoVigenteOut."""
        return DelegadoVigenteOut(
            id=uuid.UUID(result.id),
            nombre_completo=result.nombre_completo,
            cip=result.cip,
            especialidad=DelegadoPresenter._map_especialidad_revision(
                result.especialidad
            ),
            tipo=result.tipo,
        )

    @staticmethod
    def present_delegados_vigentes(
        domain_result: DelegadosVigentesResult,
    ) -> DelegadosVigentesOut:
        """Maps DelegadosVigentesResult to DelegadosVigentesOut."""
        return DelegadosVigentesOut(
            delegados=[
                DelegadoPresenter._map_delegado_vigente(item)
                for item in domain_result.delegados
            ]
        )

    @staticmethod
    def _map_tipo_liquidacion_minimal(
        result: TipoLiquidacionMinimalResult,
    ) -> "TipoLiquidacionMinimalOut":
        """Maps TipoLiquidacionMinimalResult to TipoLiquidacionMinimalOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            TipoLiquidacionMinimalOut,
        )
        return TipoLiquidacionMinimalOut(
            codigo=result.codigo,
            nombre=result.nombre,
        )

    @staticmethod
    def _map_liquidacion_delegado_liquidacion(
        result: LiquidacionDelegadoLiquidacionMinimal,
    ) -> "LiquidacionDelegadoLiquidacionOut":
        """Maps LiquidacionDelegadoLiquidacionMinimal to LiquidacionDelegadoLiquidacionOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            LiquidacionDelegadoLiquidacionOut,
        )
        return LiquidacionDelegadoLiquidacionOut(
            id=uuid.UUID(result.id),
            expediente=result.expediente,
            numero_revision=result.numero_revision,
            sub_total=float(result.sub_total) if result.sub_total is not None else None,
            total=float(result.total) if result.total is not None else None,
            municipalidad_nombre=result.municipalidad_nombre,
            proyecto_denominacion=result.proyecto_denominacion,
            tipo_liquidacion=(
                DelegadoPresenter._map_tipo_liquidacion_minimal(result.tipo_liquidacion)
                if result.tipo_liquidacion
                else None
            ),
        )

    @staticmethod
    def _map_liquidacion_delegado_delegado(
        result: LiquidacionDelegadoDelegadoMinimal,
    ) -> "LiquidacionDelegadoDelegadoOut":
        """Maps LiquidacionDelegadoDelegadoMinimal to LiquidacionDelegadoDelegadoOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            LiquidacionDelegadoDelegadoOut,
        )
        return LiquidacionDelegadoDelegadoOut(
            id=uuid.UUID(result.id),
            cip=result.cip,
            dni=result.dni,
            nombre_completo=result.nombre_completo,
        )

    @staticmethod
    def _map_liquidacion_delegado(
        result: LiquidacionDelegadoResult,
    ) -> LiquidacionDelegadoOut:
        """Maps LiquidacionDelegadoResult to LiquidacionDelegadoOut."""
        return LiquidacionDelegadoOut(
            id=uuid.UUID(result.id),
            liquidacion_id=uuid.UUID(result.liquidacion_id),
            delegado_id=uuid.UUID(result.delegado_id),
            especialidad_revision=DelegadoPresenter._map_especialidad_revision(
                result.especialidad_revision
            ),
            liquidacion=(
                DelegadoPresenter._map_liquidacion_delegado_liquidacion(result.liquidacion)
                if result.liquidacion
                else None
            ),
            delegado=(
                DelegadoPresenter._map_liquidacion_delegado_delegado(result.delegado)
                if result.delegado
                else None
            ),
            periodo=result.periodo,
            mes=result.mes,
            dictamen_revision=result.dictamen_revision,
            fecha_presentacion=(
                result.fecha_presentacion.isoformat()
                if result.fecha_presentacion
                else None
            ),
            fecha_revision=(
                result.fecha_revision.isoformat()
                if result.fecha_revision
                else None
            ),
        )

    @staticmethod
    def present_liquidacion_delegado_batch(
        domain_result: LiquidacionDelegadoBatchResult,
    ) -> LiquidacionDelegadoBatchOut:
        """Maps LiquidacionDelegadoBatchResult to LiquidacionDelegadoBatchOut."""
        return LiquidacionDelegadoBatchOut(
            created=[
                DelegadoPresenter._map_liquidacion_delegado(item)
                for item in domain_result.created
            ],
            updated=[
                DelegadoPresenter._map_liquidacion_delegado(item)
                for item in domain_result.updated
            ],
            deleted=domain_result.deleted,
        )

    @staticmethod
    def present_asignaciones_list(
        results: List[LiquidacionDelegadoResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionDelegadoOut]:
        """
        Maps a list of LiquidacionDelegadoResult + pagination metadata
        to PaginatedData[LiquidacionDelegadoOut].
        """
        items: List[LiquidacionDelegadoOut] = [
            DelegadoPresenter._map_liquidacion_delegado(item)
            for item in results
        ]
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_candidatas(
        domain_result: "DelegadoCandidatasResult",
    ) -> "DelegadoCandidatasOut":
        """Maps DelegadoCandidatasResult to DelegadoCandidatasOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            DelegadoCandidatasOut,
            CandidataOut,
            ComprobanteActivoMinimalOut,
        )
        candidatas = []
        for c in domain_result.candidatas:
            # Map comprobante_activo if present
            comprobante_activo_out = None
            if c.comprobante_activo:
                comprobante_activo_out = ComprobanteActivoMinimalOut(
                    tipo_comprobante=c.comprobante_activo.tipo_comprobante,
                    serie=c.comprobante_activo.serie,
                    numero=c.comprobante_activo.numero,
                    fecha_emision=c.comprobante_activo.fecha_emision,
                )
            
            candidatas.append(CandidataOut(
                id=uuid.UUID(c.id),
                expediente=c.expediente,
                numero_revision=c.numero_revision,
                sub_total=c.sub_total,
                total=c.total,
                municipalidad_nombre=c.municipalidad_nombre,
                proyecto_denominacion=c.proyecto_denominacion,
                tipo_liquidacion=(
                    DelegadoPresenter._map_tipo_liquidacion_minimal(c.tipo_liquidacion)
                    if c.tipo_liquidacion
                    else None
                ),
                especialidad_candidata=DelegadoPresenter._map_especialidad_revision(
                    c.especialidad_candidata
                ),
                tipo_delegado=c.tipo_delegado,
                delegado_operacion_id=uuid.UUID(c.delegado_operacion_id),
                liquidacion_especifica_numero=c.liquidacion_especifica_numero,
                comprobante_activo=comprobante_activo_out,
            ))
        
        return DelegadoCandidatasOut(
            delegado=DelegadoPresenter._map_liquidacion_delegado_delegado(domain_result.delegado),
            candidatas=candidatas,
            total=domain_result.total,
        )

    @staticmethod
    def present_candidatas_paginated(
        domain_result: "DelegadoCandidatasPaginatedResult",
    ) -> "DelegadoCandidatasPaginatedOut":
        """Maps DelegadoCandidatasPaginatedResult to DelegadoCandidatasPaginatedOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            DelegadoCandidatasPaginatedOut,
            CandidataOut,
            ComprobanteActivoMinimalOut,
        )
        items = []
        for c in domain_result.items:
            comprobante_activo_out = None
            if c.comprobante_activo:
                comprobante_activo_out = ComprobanteActivoMinimalOut(
                    tipo_comprobante=c.comprobante_activo.tipo_comprobante,
                    serie=c.comprobante_activo.serie,
                    numero=c.comprobante_activo.numero,
                    fecha_emision=c.comprobante_activo.fecha_emision,
                )

            items.append(CandidataOut(
                id=uuid.UUID(c.id),
                expediente=c.expediente,
                numero_revision=c.numero_revision,
                sub_total=c.sub_total,
                total=c.total,
                municipalidad_nombre=c.municipalidad_nombre,
                proyecto_denominacion=c.proyecto_denominacion,
                tipo_liquidacion=(
                    DelegadoPresenter._map_tipo_liquidacion_minimal(c.tipo_liquidacion)
                    if c.tipo_liquidacion
                    else None
                ),
                especialidad_candidata=DelegadoPresenter._map_especialidad_revision(
                    c.especialidad_candidata
                ),
                tipo_delegado=c.tipo_delegado,
                delegado_operacion_id=uuid.UUID(c.delegado_operacion_id),
                liquidacion_especifica_numero=c.liquidacion_especifica_numero,
                comprobante_activo=comprobante_activo_out,
            ))

        return DelegadoCandidatasPaginatedOut(
            delegado=DelegadoPresenter._map_liquidacion_delegado_delegado(domain_result.delegado),
            items=items,
            total=domain_result.total,
            page=domain_result.page,
            page_size=domain_result.page_size,
            total_pages=domain_result.total_pages,
        )

    @staticmethod
    def present_tipos_liquidacion(
        tipos: list,
    ) -> "DelegadoTiposLiquidacionOut":
        """Maps a list of TipoLiquidacion ORM objects to DelegadoTiposLiquidacionOut."""
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            DelegadoTiposLiquidacionOut,
            TipoLiquidacionListItem,
        )
        return DelegadoTiposLiquidacionOut(
            tipos=[
                TipoLiquidacionListItem(
                    id=t.id,
                    codigo=t.codigo,
                    nombre=t.nombre,
                )
                for t in tipos
            ]
        )

    @staticmethod
    def present_operatividades_vigentes(
        domain_result: "DelegadoOperatividadesVigentesResult",
    ) -> DelegadoOperatividadesVigentesOut:
        """
        Maps DelegadoOperatividadesVigentesResult to DelegadoOperatividadesVigentesOut.
        """
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            DelegadoOperatividadesVigentesOut as Out,
            DelegadoOperacionVigenteOut as OpOut,
        )

        operatividades = []
        for op in domain_result.operatividades:
            tipo_liq_id = None
            tipo_liq_codigo = None
            tipo_liq_nombre = None
            if op.tipo_liquidacion_id:
                tipo_liq_id = uuid.UUID(op.tipo_liquidacion_id) if isinstance(op.tipo_liquidacion_id, str) else op.tipo_liquidacion_id
            if op.tipo_liquidacion_codigo:
                tipo_liq_codigo = op.tipo_liquidacion_codigo
            if op.tipo_liquidacion_nombre:
                tipo_liq_nombre = op.tipo_liquidacion_nombre

            operatividades.append(OpOut(
                id=uuid.UUID(op.id),
                municipalidad_id=uuid.UUID(op.municipalidad_id),
                municipalidad_nombre=op.municipalidad_nombre,
                tipo_liquidacion_id=tipo_liq_id,
                tipo_liquidacion_codigo=tipo_liq_codigo,
                tipo_liquidacion_nombre=tipo_liq_nombre,
                especialidad_id=uuid.UUID(op.especialidad_id),
                especialidad_nombre=op.especialidad_nombre,
                tipo=op.tipo,
                periodo_inicio=op.periodo_inicio.isoformat() if op.periodo_inicio else None,
                periodo_fin=op.periodo_fin.isoformat() if op.periodo_fin else None,
            ))

        return Out(
            delegado_id=uuid.UUID(domain_result.delegado_id),
            cip=domain_result.cip,
            nombre_completo=domain_result.nombre_completo,
            operatividades=operatividades,
        )

    @staticmethod
    def present_especialidades_revision(
        domain_result: EspecialidadesRevisionResult,
    ) -> EspecialidadesRevisionOut:
        """
        Maps EspecialidadesRevisionResult to EspecialidadesRevisionOut.
        """
        return EspecialidadesRevisionOut(
            especialidades=[
                EspecialidadRevisionOpcionOut(
                    id=uuid.UUID(e.id),
                    nombre=e.nombre,
                )
                for e in domain_result.especialidades
            ]
        )
