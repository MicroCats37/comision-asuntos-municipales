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
            categoria=result.categoria,
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
                categoria=item.categoria,
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
