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
        )

    @staticmethod
    def _map_delegado(result: DelegadoResult) -> DelegadoOut:
        """Maps DelegadoResult to DelegadoOut."""
        return DelegadoOut(
            id=uuid.UUID(result.id),
            perfil_ingeniero=DelegadoPresenter._map_perfil_ingeniero(result.perfil_ingeniero),
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
                MunicipalidadesAsignadasOut(
                    id=uuid.UUID(m.id),
                    municipalidad_id=uuid.UUID(m.municipalidad_id),
                    municipalidad_nombre=m.municipalidad_nombre,
                    tipo=m.tipo,
                    categoria=m.categoria,
                    periodo_inicio=m.periodo_inicio.isoformat() if m.periodo_inicio else None,
                    periodo_fin=m.periodo_fin.isoformat() if m.periodo_fin else None,
                    es_vigente=m.es_vigente,
                )
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
