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
    InspectorVigenteFormResult,
    EspecialidadBasicaFormResult,
    InspectoresVigentesFormResult,
    LiquidacionInspectorAsignacionResult,
    LiquidacionInspectorLiquidacionMinimal,
    InspectorAsignacionInspectorMinimal,
    TipoLiquidacionMinimalResult,
    EspecialidadRevisionResult,
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
        """Builds InspectorResult from ORM object.

        tipo_liquidacion, numero_registro, telefono, email are now on
        InspectorTipoLiquidacion (accessed via inspector.tipos_liquidacion).
        """
        tipos = list(inspector.tipos_liquidacion.all())
        primer_tipo = tipos[0] if tipos else None
        return InspectorResult(
            id=str(inspector.id),
            tipo_liquidacion=primer_tipo.tipo_liquidacion.codigo if primer_tipo else "",
            numero_registro=primer_tipo.numero_registro if primer_tipo else "",
            telefono=primer_tipo.telefono if primer_tipo else None,
            email=primer_tipo.email if primer_tipo else None,
            perfil_ingeniero=self._build_perfil_ingeniero_result(inspector.perfil_ingeniero),
        )

    def _is_vigente(self, periodo, today: date) -> bool:
        """Check if a InspectorAsignacionPeriodo is vigente (active on given date)."""
        return periodo.periodo_inicio <= today and (
            periodo.periodo_fin is None or periodo.periodo_fin >= today
        )

    def _inspector_es_vigente(self, inspector, today: date) -> bool:
        """An Inspector is vigente if it has at least one InspectorAsignacionPeriodo
        vigente under any of its InspectorTipoLiquidacion records."""
        for tipo in inspector.tipos_liquidacion.all():
            for periodo in tipo.periodos.all():
                if self._is_vigente(periodo, today):
                    return True
        return False

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
            tipo_liquidacion=(
                inspector.tipos_liquidacion.all()[0].tipo_liquidacion.codigo
                if inspector.tipos_liquidacion.exists()
                else ""
            ),
            numero_registro=(
                inspector.tipos_liquidacion.all()[0].numero_registro
                if inspector.tipos_liquidacion.exists()
                else ""
            ),
            telefono=(
                inspector.tipos_liquidacion.all()[0].telefono
                if inspector.tipos_liquidacion.exists()
                else None
            ),
            email=(
                inspector.tipos_liquidacion.all()[0].email
                if inspector.tipos_liquidacion.exists()
                else None
            ),
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
        An Inspector is vigente if it has at least one InspectorAsignacionPeriodo
        vigente (under any InspectorTipoLiquidacion) with:
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
            es_vigente = self._inspector_es_vigente(inspector, today)

            domain_results.append(
                InspectorVigenteResult(
                    id=str(inspector.id),
                    tipo_liquidacion=(
                        inspector.tipos_liquidacion.all()[0].tipo_liquidacion.codigo
                        if inspector.tipos_liquidacion.exists()
                        else tipo_liquidacion
                    ),
                    numero_registro=(
                        inspector.tipos_liquidacion.all()[0].numero_registro
                        if inspector.tipos_liquidacion.exists()
                        else ""
                    ),
                    telefono=(
                        inspector.tipos_liquidacion.all()[0].telefono
                        if inspector.tipos_liquidacion.exists()
                        else None
                    ),
                    email=(
                        inspector.tipos_liquidacion.all()[0].email
                        if inspector.tipos_liquidacion.exists()
                        else None
                    ),
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

    def listar_inspectores_seleccionables_proceso(
        self,
        tipo_liquidacion: str,
        categoria: Optional[str] = None,
        q: Optional[str] = None,
    ) -> InspectoresVigentesFormResult:
        """
        Returns inspectores vigentes elegibles para el form de creación de IO,
        sin paginación.

        Filtra InspectorOperacion por:
        - tipo_liquidacion (el de la previa: EDIFICACION/HABILITACION_URBANA)
        - categoria (opcional)
        - q (búsqueda por nombre/CIP, opcional)
        - periodo vigente

        La especialidad NO es filtro — sale como dato en el output.

        Shape alineado con el alpha (InspectorVigenteResult) y el schema del
        frontend (inspector-vigente.schema.ts).
        """
        from ninja.errors import HttpError

        if not tipo_liquidacion:
            raise HttpError(400, "El parámetro tipo_liquidacion es requerido")

        today = date.today()

        operaciones = self.core_service.list_inspectores_vigentes_para_tipo(
            tipo_liquidacion=tipo_liquidacion,
            fecha=today,
            categoria=categoria,
            q=q,
        )

        inspectores: list[InspectorVigenteFormResult] = []
        for operacion in operaciones:
            perfil = operacion.inspector.perfil_ingeniero
            esp = operacion.especialidad_revision
            periodo = self._get_periodo_vigente(operacion, today)
            inspectores.append(
                InspectorVigenteFormResult(
                    id=str(operacion.inspector_id),
                    nombre_completo=perfil.nombre_completo,
                    cip=perfil.cip or "",
                    especialidad=(
                        EspecialidadBasicaFormResult(
                            id=str(esp.id),
                            nombre=esp.nombre,
                        )
                        if esp
                        else None
                    ),
                    tipo_liquidacion=(
                        operacion.tipo_liquidacion.codigo
                        if operacion.tipo_liquidacion
                        else tipo_liquidacion
                    ),
                    categoria=operacion.categoria or None,
                    numero_registro=operacion.numero_registro,
                    vigencia=str(periodo.periodo_fin) if periodo and periodo.periodo_fin else None,
                    inspector_operacion_id=str(operacion.id),
                )
            )

        return InspectoresVigentesFormResult(inspectores=inspectores)

    @staticmethod
    def _get_periodo_vigente(operacion, fecha: date):
        """Returns the vigente periodo of an InspectorOperacion, or None."""
        for periodo in operacion.periodos.all():
            if periodo.periodo_inicio <= fecha and (
                periodo.periodo_fin is None or periodo.periodo_fin >= fecha
            ):
                return periodo
        return None

    def listar_asignaciones_inspectores_proceso(
        self,
        page: int,
        page_size: int,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Returns (list[LiquidacionInspectorAsignacionResult], total) paginados
        para el selector de Recibos de Honorarios de Inspectores.

        Filtra LiquidacionInspector por cip del inspector o id de la liquidación general.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        objects, total = self.core_service.list_liquidacion_inspector_paginated(
            page=page,
            page_size=page_size,
            cip=cip,
            liquidacion_id=liquidacion_id,
        )

        results = [self._build_liquidacion_inspector_asignacion(li) for li in objects]
        return results, total

    @staticmethod
    def _build_liquidacion_inspector_asignacion(li) -> LiquidacionInspectorAsignacionResult:
        """Builds LiquidacionInspectorAsignacionResult from a LiquidacionInspector ORM object."""
        lg = li.liquidacion.liquidacion_general
        perfil = li.inspector.perfil_ingeniero

        liquidacion_min = None
        if lg is not None:
            liquidacion_min = LiquidacionInspectorLiquidacionMinimal(
                id=str(lg.id),
                expediente=lg.expediente or "",
                numero_revision=lg.numero_revision,
                sub_total=float(lg.sub_total) if lg.sub_total is not None else None,
                total=float(lg.total) if lg.total is not None else None,
                municipalidad_nombre=(
                    lg.municipalidad.nombre if lg.municipalidad else None
                ),
                proyecto_denominacion=(
                    lg.proyecto.nombre_propietario if lg.proyecto else None
                ),
                tipo_liquidacion=(
                    TipoLiquidacionMinimalResult(
                        codigo=lg.tipo_liquidacion.codigo,
                        nombre=lg.tipo_liquidacion.nombre,
                    )
                    if lg.tipo_liquidacion
                    else None
                ),
            )

        return LiquidacionInspectorAsignacionResult(
            id=str(li.id),
            liquidacion_id=str(li.liquidacion_id),
            inspector_id=str(li.inspector_id),
            especialidad_revision=(
                EspecialidadRevisionResult(
                    id=str(li.especialidad_revision.id),
                    nombre=li.especialidad_revision.nombre,
                )
                if li.especialidad_revision
                else None
            ),
            liquidacion=liquidacion_min,
            inspector=InspectorAsignacionInspectorMinimal(
                id=str(li.inspector.id),
                cip=perfil.cip or "",
                dni=perfil.dni or "",
                nombre_completo=perfil.nombre_completo,
            ),
            periodo=li.periodo,
            mes=li.mes,
            dictamen_revision=li.dictamen_revision,
            fecha_presentacion=(
                str(li.fecha_presentacion) if li.fecha_presentacion else None
            ),
            fecha_revision=str(li.fecha_revision) if li.fecha_revision else None,
        )
