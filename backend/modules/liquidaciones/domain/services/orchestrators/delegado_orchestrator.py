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
        )

    def _build_delegado_result(self, delegado) -> DelegadoResult:
        """Builds DelegadoResult from ORM object."""
        return DelegadoResult(
            id=str(delegado.id),
            perfil_ingeniero=self._build_perfil_ingeniero_result(delegado.perfil_ingeniero),
        )

    def list_delegados_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> DelegadoListResult:
        """
        Returns paginated list of DelegadoResult.
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
        )

        domain_results: list[DelegadoResult] = [
            self._build_delegado_result(d) for d in orm_objects
        ]

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

        municipalidades_result: list[MunicipalidadesAsignadasResult] = []
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

            municipalidades_result.append(
                MunicipalidadesAsignadasResult(
                    id=str(dm.id),
                    municipalidad_id=str(dm.municipalidad_id),
                    municipalidad_nombre=dm.municipalidad.nombre if dm.municipalidad else "",
                    tipo=dm.tipo or "",
                    categoria=dm.categoria,
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    es_vigente=es_vigente,
                )
            )

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
                    categoria=dm.categoria,
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    es_vigente=es_vigente,
                )
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return DelegadosPorMunicipalidadResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
