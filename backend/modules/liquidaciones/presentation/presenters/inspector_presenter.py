"""
InspectorPresenter — Maps Domain Results to API Schema Out.

NO ORM. Only @staticmethod. Only maps Result → Schema Out.
"""
import uuid
from typing import List

from modules.liquidaciones.domain.results.inspector.inspector_result import (
    PerfilIngenieroResult,
    InspectorResult,
    InspectorListResult,
    InspectorDetailResult,
    InspectorVigenteResult,
    InspectorVigenteListResult,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_schemas import (
    PerfilIngenieroOut,
    InspectorOut,
    InspectorListOut,
    InspectorDetailOut,
    InspectorVigenteOut,
    InspectorVigenteListOut,
)
from core.pagination import PaginatedData


class InspectorPresenter:
    """
    Presenter for Inspector endpoints.
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
    def _map_inspector(result: InspectorResult) -> InspectorOut:
        """Maps InspectorResult to InspectorOut."""
        return InspectorOut(
            id=uuid.UUID(result.id),
            tipo_liquidacion=result.tipo_liquidacion,
            numero_registro=result.numero_registro,
            telefono=result.telefono,
            email=result.email,
            perfil_ingeniero=InspectorPresenter._map_perfil_ingeniero(result.perfil_ingeniero),
        )

    @staticmethod
    def present_list(domain_result: InspectorListResult) -> PaginatedData[InspectorOut]:
        """
        Maps InspectorListResult to PaginatedData[InspectorOut].
        """
        items: List[InspectorOut] = [
            InspectorPresenter._map_inspector(item)
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
    def present_detail(domain_result: InspectorDetailResult) -> InspectorDetailOut:
        """
        Maps InspectorDetailResult to InspectorDetailOut.
        """
        return InspectorDetailOut(
            id=uuid.UUID(domain_result.id),
            tipo_liquidacion=domain_result.tipo_liquidacion,
            numero_registro=domain_result.numero_registro,
            telefono=domain_result.telefono,
            email=domain_result.email,
            perfil_ingeniero=InspectorPresenter._map_perfil_ingeniero(domain_result.perfil_ingeniero),
        )

    @staticmethod
    def _map_inspector_vigente(result: InspectorVigenteResult) -> InspectorVigenteOut:
        """Maps InspectorVigenteResult to InspectorVigenteOut."""
        return InspectorVigenteOut(
            id=uuid.UUID(result.id),
            tipo_liquidacion=result.tipo_liquidacion,
            numero_registro=result.numero_registro,
            telefono=result.telefono,
            email=result.email,
            perfil_ingeniero=InspectorPresenter._map_perfil_ingeniero(result.perfil_ingeniero),
            es_vigente=result.es_vigente,
        )

    @staticmethod
    def present_vigentes(domain_result: InspectorVigenteListResult) -> PaginatedData[InspectorVigenteOut]:
        """
        Maps InspectorVigenteListResult to PaginatedData[InspectorVigenteOut].
        """
        items: List[InspectorVigenteOut] = [
            InspectorPresenter._map_inspector_vigente(item)
            for item in domain_result.items
        ]
        return PaginatedData(
            items=items,
            total=domain_result.total,
            page=domain_result.page,
            page_size=domain_result.page_size,
            total_pages=domain_result.total_pages,
        )
