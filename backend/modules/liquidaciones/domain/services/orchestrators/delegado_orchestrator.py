"""
DelegadoOrchestrator — builds Domain DTOs from ORM objects.

Validates input, calls Core, maps ORM → Domain Result.
"""
import uuid
import math
from datetime import date
from typing import Optional

from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.domain.results.delegado.delegado_result import (
    PerfilIngenieroResult,
    DelegadoResult,
    DelegadoListResult,
    MunicipalidadesAsignadasResult,
    DelegadoMunicipalidadesResult,
    DelegadoForMunicipalidadResult,
    DelegadosPorMunicipalidadResult,
    EspecialidadResult,
    CapituloResult,
    MunicipalidadBasicResult,
)


class DelegadoOrchestrator:
    """
    Orchestrator for Delegado endpoints.

    Responsibilities:
    - Input validation
    - Calls Core for ORM operations
    - Builds Domain Results from ORM objects
    - Raises HttpError if not found
    """

    @inject
    def __init__(
        self,
        core_service: DelegadoCoreService,
    ):
        self.core_service = core_service

    def _build_perfil_ingeniero_result(self, perfil) -> PerfilIngenieroResult:
        """Builds PerfilIngenieroResult from ORM object."""
        especialidad_result = None
        if getattr(perfil, "especialidad", None):
            especialidad_result = EspecialidadResult(
                id=str(perfil.especialidad.id),
                codigo=perfil.especialidad.codigo,
                nombre=perfil.especialidad.nombre,
            )
        capitulo_result = None
        if getattr(perfil, "capitulo", None):
            capitulo_result = CapituloResult(
                id=str(perfil.capitulo.id),
                registro_id=perfil.capitulo.registro_id,
                abreviacion=perfil.capitulo.abreviacion,
                nombre=perfil.capitulo.nombre,
            )
        return PerfilIngenieroResult(
            id=str(perfil.id),
            cip=perfil.cip or "",
            dni=perfil.dni or "",
            nombres=perfil.nombres or "",
            apellido_paterno=perfil.apellido_paterno or "",
            apellido_materno=perfil.apellido_materno or "",
            nombre_completo=perfil.nombre_completo,
            correo_personal=perfil.correo_personal,
            correo_institucional=perfil.correo_institucional,
            especialidad=especialidad_result,
            capitulo=capitulo_result,
        )

    def _build_municipalidad_asignada_result(self, dm, today: date) -> MunicipalidadesAsignadasResult:
        """Builds MunicipalidadesAsignadasResult from a DelegadoMunicipalidad ORM object."""
        current_periodo = None
        for periodo in dm.periodos.all():
            if periodo.periodo_inicio <= today and (
                periodo.periodo_fin is None or periodo.periodo_fin >= today
            ):
                current_periodo = periodo
                break

        return MunicipalidadesAsignadasResult(
            id=str(dm.id),
            municipalidad=MunicipalidadBasicResult(
                id=str(dm.municipalidad.id),
                codigo=dm.municipalidad.codigo,
                nombre=dm.municipalidad.nombre,
            ),
            tipo=dm.tipo or "",
            periodo_inicio=current_periodo.periodo_inicio if current_periodo else None,
            periodo_fin=current_periodo.periodo_fin if current_periodo else None,
            es_vigente=current_periodo is not None,
        )

    def _build_delegado_result(self, delegado, today: date) -> DelegadoResult:
        """Builds DelegadoResult from ORM object, incluyendo municipalidades y estado."""
        municipalidades = [
            self._build_municipalidad_asignada_result(dm, today)
            for dm in delegado.municipalidades_asignadas.all()
        ]

        if not municipalidades:
            estado = "sin_asignaciones"
        elif any(m.es_vigente for m in municipalidades):
            estado = "vigente"
        else:
            estado = "sin_vigencia"

        return DelegadoResult(
            id=str(delegado.id),
            perfil_ingeniero=self._build_perfil_ingeniero_result(delegado.perfil_ingeniero),
            municipalidades=municipalidades,
            estado=estado,
        )

    def list_delegados_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        capitulo_id: Optional[uuid.UUID] = None,
        especialidad_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
    ) -> DelegadoListResult:
        """
        Returns paginated list of DelegadoResult con municipalidades y estado.
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.core_service.list_delegados_paginated(
            page=page,
            page_size=page_size,
            cip=cip,
            municipalidad_id=municipalidad_id,
            capitulo_id=capitulo_id,
            especialidad_id=especialidad_id,
        )

        today = date.today()
        domain_results: list[DelegadoResult] = [
            self._build_delegado_result(d, today) for d in orm_objects
        ]

        # Filtro por estado (post-proceso porque es derivado)
        if estado:
            domain_results = [d for d in domain_results if d.estado == estado]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return DelegadoListResult(
            items=domain_results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def obtener_municipalidades_proceso(
        self,
        delegado_id: uuid.UUID,
    ) -> DelegadoMunicipalidadesResult:
        """
        Returns all municipalidad assignments for a delegado with vigencia status.
        Raises HttpError 404 if delegado not found.
        """
        delegado = self.core_service.get_delegado_by_id(delegado_id)
        if not delegado:
            raise HttpError(404, f"Delegado '{delegado_id}' no encontrado")

        dm_list = self.core_service.get_municipalidades_for_delegado(delegado_id)
        today = date.today()

        municipalidades_result: list[MunicipalidadesAsignadasResult] = [
            self._build_municipalidad_asignada_result(dm, today)
            for dm in dm_list
        ]

        return DelegadoMunicipalidadesResult(
            delegado_id=str(delegado.id),
            perfil_ingeniero=self._build_perfil_ingeniero_result(delegado.perfil_ingeniero),
            municipalidades=municipalidades_result,
        )

    def list_delegados_por_municipalidad_proceso(
        self,
        municipalidad_id: uuid.UUID,
        vigente: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> DelegadosPorMunicipalidadResult:
        """
        Returns all delegados for a municipalidad with optional vigencia filter.
        vigencia filter: periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today)
        """
        # Normalize vigente string→bool (controller passes raw query param)
        if isinstance(vigente, str):
            vigente = vigente.lower() == "true"

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        dm_list, total = self.core_service.get_delegados_for_municipalidad(
            municipalidad_id=municipalidad_id,
            vigente=vigente,
            page=page,
            page_size=page_size,
        )

        today = date.today()
        items: list[DelegadoForMunicipalidadResult] = []

        for dm in dm_list:
            current_periodo = None
            for periodo in dm.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break

            es_vigente = current_periodo is not None
            periodo_inicio = current_periodo.periodo_inicio if current_periodo else None
            periodo_fin = current_periodo.periodo_fin if current_periodo else None

            items.append(
                DelegadoForMunicipalidadResult(
                    id=str(dm.delegado.id),
                    perfil_ingeniero=self._build_perfil_ingeniero_result(dm.delegado.perfil_ingeniero),
                    tipo=dm.tipo or "",
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    es_vigente=es_vigente,
                )
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        # Post-filter: when vigente=False, exclude vigentes (computed in loop above)
        if vigente is False:
            items = [i for i in items if not i.es_vigente]

        return DelegadosPorMunicipalidadResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
