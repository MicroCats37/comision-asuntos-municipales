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
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_schemas import (
    PerfilIngenieroOut,
    DelegadoOut,
    DelegadoListOut,
    MunicipalidadesAsignadasOut,
    DelegadoMunicipalidadesOut,
    DelegadoForMunicipalidadOut,
    DelegadosPorMunicipalidadOut,
    EspecialidadOut,
    CapituloOut,
    MunicipalidadBasicOut,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    EspecialidadRevisionOut,
    DelegadoVigenteOut,
    DelegadosVigentesOut,
    LiquidacionDelegadoOut,
    LiquidacionDelegadoBatchOut,
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
