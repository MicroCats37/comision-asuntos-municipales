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
    InspectorVigenteFormResult,
    EspecialidadBasicaFormResult,
    InspectoresVigentesFormResult,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_schemas import (
    PerfilIngenieroOut,
    InspectorOut,
    InspectorListOut,
    InspectorDetailOut,
    InspectorVigenteOut,
    InspectorVigenteListOut,
    EspecialidadBasicaInspectorOut,
    InspectorSeleccionableOut,
    InspectoresSeleccionablesOut,
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

    @staticmethod
    def present_seleccionables(
        domain_result: InspectoresVigentesFormResult,
    ) -> InspectoresSeleccionablesOut:
        """
        Maps InspectoresVigentesFormResult to InspectoresSeleccionablesOut.

        Para el form de creación de IO. Shape alineado con el alpha y el
        schema del frontend (inspector-vigente.schema.ts).

        especialidad es siempre requerida: InspectorOperacion.especialidad_revision
        es NOT NULL en el refactor.
        """
        inspectores: List[InspectorSeleccionableOut] = []
        for item in domain_result.inspectores:
            inspectores.append(
                InspectorSeleccionableOut(
                    id=uuid.UUID(item.id),
                    nombre_completo=item.nombre_completo,
                    cip=item.cip,
                    especialidad=EspecialidadBasicaInspectorOut(
                        id=uuid.UUID(item.especialidad.id),
                        nombre=item.especialidad.nombre,
                    ),
                    tipo_liquidacion=item.tipo_liquidacion,
                    categoria=item.categoria,
                    numero_registro=item.numero_registro,
                    vigencia=item.vigencia,
                    inspector_operacion_id=uuid.UUID(item.inspector_operacion_id),
                )
            )
        return InspectoresSeleccionablesOut(inspectores=inspectores)

    @staticmethod
    def present_asignaciones_inspectores_list(
        results,
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData:
        """
        Maps list[LiquidacionInspectorAsignacionResult] to
        PaginatedData[LiquidacionInspectorAsignacionOut].
        """
        from modules.liquidaciones.presentation.schemas.inspector.inspector_schemas import (
            LiquidacionInspectorAsignacionOut,
            LiquidacionInspectorLiquidacionOut,
            InspectorAsignacionInspectorOut,
            EspecialidadRevisionInspectorOut,
            TipoLiquidacionMinimalOut,
        )

        import math

        items = []
        for r in results:
            items.append(
                LiquidacionInspectorAsignacionOut(
                    id=uuid.UUID(r.id),
                    liquidacion_id=uuid.UUID(r.liquidacion_id),
                    inspector_id=uuid.UUID(r.inspector_id),
                    especialidad_revision=(
                        EspecialidadRevisionInspectorOut(
                            id=uuid.UUID(r.especialidad_revision.id),
                            nombre=r.especialidad_revision.nombre,
                        )
                        if r.especialidad_revision
                        else None
                    ),
                    liquidacion=(
                        LiquidacionInspectorLiquidacionOut(
                            id=uuid.UUID(r.liquidacion.id),
                            expediente=r.liquidacion.expediente,
                            numero_revision=r.liquidacion.numero_revision,
                            sub_total=r.liquidacion.sub_total,
                            total=r.liquidacion.total,
                            municipalidad_nombre=r.liquidacion.municipalidad_nombre,
                            proyecto_denominacion=r.liquidacion.proyecto_denominacion,
                            tipo_liquidacion=(
                                TipoLiquidacionMinimalOut(
                                    codigo=r.liquidacion.tipo_liquidacion.codigo,
                                    nombre=r.liquidacion.tipo_liquidacion.nombre,
                                )
                                if r.liquidacion.tipo_liquidacion
                                else None
                            ),
                        )
                        if r.liquidacion
                        else None
                    ),
                    inspector=(
                        InspectorAsignacionInspectorOut(
                            id=uuid.UUID(r.inspector.id),
                            cip=r.inspector.cip,
                            dni=r.inspector.dni,
                            nombre_completo=r.inspector.nombre_completo,
                        )
                        if r.inspector
                        else None
                    ),
                    periodo=r.periodo,
                    mes=r.mes,
                    dictamen_revision=r.dictamen_revision,
                    fecha_presentacion=r.fecha_presentacion,
                    fecha_revision=r.fecha_revision,
                )
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
