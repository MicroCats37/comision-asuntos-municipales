"""
InspectorOrchestrator — builds Domain DTOs from ORM objects.

Validates input, calls Core, maps ORM → Domain Result.
"""
import uuid
import math
from datetime import date
from typing import Optional

from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.inspector.inspector_core_service import (
    InspectorCoreService,
)
from modules.liquidaciones.domain.results.inspector.inspector_result import (
    PerfilIngenieroResult,
    InspectorResult,
    InspectorListResult,
    InspectorDetailResult,
    InspectorVigenteResult,
    InspectorVigenteListResult,
)


class InspectorOrchestrator:
    """
    Orchestrator for Inspector endpoints.

    Responsibilities:
    - Input validation
    - Calls Core for ORM operations
    - Builds Domain Results from ORM objects
    - Raises HttpError if not found
    """

    @inject
    def __init__(
        self,
        core_service: InspectorCoreService,
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

    def _build_inspector_result(self, inspector) -> InspectorResult:
        """Builds InspectorResult from ORM object."""
        return InspectorResult(
            id=str(inspector.id),
            tipo_liquidacion=inspector.tipo_liquidacion.codigo,
            numero_registro=inspector.numero_registro,
            telefono=inspector.telefono,
            email=inspector.email,
            perfil_ingeniero=self._build_perfil_ingeniero_result(inspector.perfil_ingeniero),
        )

    def _is_vigente(self, periodo, today: date) -> bool:
        """Check if a InspectorPeriodo is vigente (active on given date)."""
        return periodo.periodo_inicio <= today and (
            periodo.periodo_fin is None or periodo.periodo_fin >= today
        )

    def list_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> InspectorListResult:
        """
        Returns paginated list of InspectorResult.
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.core_service.list_inspectores_paginated(
            page=page,
            page_size=page_size,
        )

        domain_results: list[InspectorResult] = [
            self._build_inspector_result(i) for i in orm_objects
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return InspectorListResult(
            items=domain_results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def obtener_inspector_proceso(
        self,
        inspector_id: uuid.UUID,
    ) -> InspectorDetailResult:
        """
        Returns detail for a single Inspector.
        Raises HttpError 404 if not found.
        """
        inspector = self.core_service.get_inspector_by_id(inspector_id)
        if not inspector:
            raise HttpError(404, f"Inspector '{inspector_id}' no encontrado")

        return InspectorDetailResult(
            id=str(inspector.id),
            tipo_liquidacion=inspector.tipo_liquidacion.codigo,
            numero_registro=inspector.numero_registro,
            telefono=inspector.telefono,
            email=inspector.email,
            perfil_ingeniero=self._build_perfil_ingeniero_result(inspector.perfil_ingeniero),
        )

    def list_inspectores_vigentes_proceso(
        self,
        tipo_liquidacion: str,
        page: int = 1,
        page_size: int = 10,
    ) -> InspectorVigenteListResult:
        """
        Returns paginated list of vigentes Inspectores filtered by tipo_liquidacion.
        An Inspector is vigente if it has at least one InspectorPeriodo with:
        periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today).
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.core_service.list_inspectores_vigentes(
            tipo_liquidacion=tipo_liquidacion,
            page=page,
            page_size=page_size,
        )

        today = date.today()

        domain_results: list[InspectorVigenteResult] = []
        for inspector in orm_objects:
            # Check if inspector has any vigente periodo
            periodos = list(inspector.municipalidades_asignadas.all())
            es_vigente = any(
                self._is_vigente(p, today) for p in periodos
            )

            domain_results.append(
                InspectorVigenteResult(
                    id=str(inspector.id),
                    tipo_liquidacion=inspector.tipo_liquidacion.codigo,
                    numero_registro=inspector.numero_registro,
                    telefono=inspector.telefono,
                    email=inspector.email,
                    perfil_ingeniero=self._build_perfil_ingeniero_result(inspector.perfil_ingeniero),
                    es_vigente=es_vigente,
                )
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return InspectorVigenteListResult(
            items=domain_results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
