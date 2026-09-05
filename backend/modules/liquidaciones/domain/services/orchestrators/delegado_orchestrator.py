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
    DelegadoCandidatasResult,
    CandidataResult,
    LiquidacionDelegadoDelegadoMinimal,
    TipoLiquidacionMinimalResult,
    EspecialidadRevisionResult,
    DelegadoOperatividadesVigentesResult,
    DelegadoOperacionVigenteResult,
    ComprobanteActivoMinimal,
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
        return self.core_service.build_municipalidad_asignada_result(dm, today)

    def _build_delegado_result(self, delegado, today: date) -> DelegadoResult:
        """Builds DelegadoResult from ORM object, incluyendo municipalidades y estado."""
        municipalidades = [
            self.core_service.build_municipalidad_asignada_result(dm, today)
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
            items.append(
                self.core_service.build_delegado_for_municipalidad_result(dm, today)
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

    def list_candidatas_delegado_proceso(
        self,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        tipo_liquidacion_id: Optional[uuid.UUID] = None,
        tipo_delegado: Optional[str] = None,
        delegado_operacion_id: Optional[uuid.UUID] = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> DelegadoCandidatasResult:
        """
        Returns DelegadoCandidatasResult (domain DTO) of candidate liquidaciones for
        the resolved DelegadoOperacion.

        Path 1 — SmartField (delegado_operacion_id provided):
          - Resolve DelegadoOperacion directly by ID.
          - Validate it belongs to cip (if cip provided).
          - Validate it is vigente (current active).
          - Use operation's municipalidad/especialidad/tipo to filter candidatas.

        Path 2 — Filter-based (delegado_operacion_id NOT provided):
          - Resolves exactly ONE active DelegadoOperacion using:
            cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + current vigency.
          - Raises 404 if no operation found. Raises 409 if multiple operations match.

        The resolved operation's especialidad_revision_id is used internally to filter candidatas.

        Args:
            cip: CIP of the delegado (required for filter-based path).
            municipalidad_id: UUID of the municipalidad (required for filter-based path).
            tipo_liquidacion_id: UUID of the TipoLiquidacion (required for filter-based path).
            tipo_delegado: TITULAR or ALTERNO (required for filter-based path).
            delegado_operacion_id: Optional — if provided, use this operation directly.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Raises:
            404 if no operation found or delegado with cip not found.
            409 if multiple operations match (config ambiguity).
        """
        from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion

        today = date.today()

        if delegado_operacion_id is not None:
            # ── Path 1: SmartField — resolve operation directly by ID ──────────
            operacion = self.core_service.get_delegado_operacion_by_id(delegado_operacion_id)
            if not operacion:
                raise HttpError(404, f"DelegadoOperacion '{delegado_operacion_id}' no encontrada")

            # If cip provided, validate operation belongs to this delegado
            if cip:
                delegado = Delegado.objects.select_related(
                    "perfil_ingeniero"
                ).filter(perfil_ingeniero__cip=cip).first()
                if not delegado:
                    raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")
                if str(operacion.delegado_id) != str(delegado.id):
                    raise HttpError(
                        400,
                        f"La operatividad '{delegado_operacion_id}' no pertenece al delegado '{cip}'",
                    )
                final_delegado = delegado
            else:
                # No cip validation — get delegado from operation
                final_delegado = operacion.delegado

            # Validate operation is vigente (has current periodo)
            current_periodo = None
            for periodo in operacion.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break
            if current_periodo is None:
                raise HttpError(
                    404,
                    f"La operatividad '{delegado_operacion_id}' no está vigente",
                )

            # Get candidatas using the operation directly
            candidatas_tuples = self.core_service.get_candidatas_for_delegado(
                final_delegado, today,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                operacion=operacion,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(final_delegado.id),
                cip=final_delegado.perfil_ingeniero.cip or "",
                dni=final_delegado.perfil_ingeniero.dni or "",
                nombre_completo=final_delegado.perfil_ingeniero.nombre_completo,
            )

        else:
            # ── Path 2: Filter-based — resolve operation from filters ───────────
            if not all([cip, municipalidad_id, tipo_liquidacion_id, tipo_delegado]):
                raise HttpError(
                    400,
                    "Se requiere cip, municipalidad_id, tipo_liquidacion_id y tipo_delegado, "
                    "o delegadow_operacion_id",
                )

            delegado = Delegado.objects.select_related(
                "perfil_ingeniero"
            ).filter(perfil_ingeniero__cip=cip).first()

            if not delegado:
                raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")

            # Resolve exactly one active DelegadoOperacion matching the given criteria.
            # Raises 404 if none found, 409 if more than one matches (ambiguity).
            operacion = self.core_service.resolve_delegado_operacion(
                delegado=delegado,
                municipalidad_id=municipalidad_id,
                tipo_liquidacion_id=tipo_liquidacion_id,
                tipo_delegado=tipo_delegado,
                fecha=today,
            )

            # Get candidatas filtered by the resolved operation's especialidad.
            candidatas_tuples = self.core_service.get_candidatas_for_delegado(
                delegado, today,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                operacion=operacion,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(delegado.id),
                cip=delegado.perfil_ingeniero.cip or "",
                dni=delegado.perfil_ingeniero.dni or "",
                nombre_completo=delegado.perfil_ingeniero.nombre_completo,
            )

        # Map tipo_liquidacion.codigo -> related_name for specific OneToOne models
        _TIPO_CODIGO_TO_RELATED_NAME = {
            "EDIFICACION": "edificaciones",
            "HABILITACION_URBANA": "habilitacion_urbana",
            "MECANICA_SUELOS": "mecanica_suelos",
            "IMPACTO_VIAL": "impacto_vial",
            "TALUDES": "taludes",
            "INSPECCION_OBRA": "inspeccion_obra",
        }

        candidatas_list = []
        for liq, especialidad, tipo, op in candidatas_tuples:
            # Extract liquidacion_especifica_numero from the specific OneToOne model
            liq_especifica_numero = None
            if liq.tipo_liquidacion and liq.tipo_liquidacion.codigo:
                _related_name = _TIPO_CODIGO_TO_RELATED_NAME.get(liq.tipo_liquidacion.codigo)
                if _related_name:
                    specific = getattr(liq, _related_name, None)
                    if specific and hasattr(specific, "numero"):
                        liq_especifica_numero = specific.numero

            # Extract comprobante_activo from prefetched comprovantes
            comprobante_activo = None
            for comp in liq.comprobantes.all():
                if comp.activo:
                    comprobante_activo = ComprobanteActivoMinimal(
                        tipo_comprobante=comp.tipo_comprobante,
                        serie=comp.serie,
                        numero=comp.numero,
                        fecha_emision=comp.fecha_emision.isoformat() if comp.fecha_emision else None,
                    )
                    break

            candidatas_list.append(CandidataResult(
                id=str(liq.id),
                expediente=getattr(liq, "expediente", None),
                numero_revision=getattr(liq, "numero_revision", 1),
                sub_total=float(liq.sub_total) if getattr(liq, "sub_total", None) else None,
                total=float(liq.total) if getattr(liq, "total", None) else None,
                municipalidad_nombre=liq.municipalidad.nombre if liq.municipalidad else None,
                proyecto_denominacion=getattr(liq, "denominacion_de_proyecto", None),
                tipo_liquidacion=TipoLiquidacionMinimalResult(
                    codigo=liq.tipo_liquidacion.codigo,
                    nombre=liq.tipo_liquidacion.nombre,
                ) if liq.tipo_liquidacion else None,
                especialidad_candidata=EspecialidadRevisionResult(
                    id=str(especialidad.id),
                    nombre=especialidad.nombre,
                ),
                tipo_delegado=tipo,
                delegado_operacion_id=str(op.id),
                liquidacion_especifica_numero=liq_especifica_numero,
                comprobante_activo=comprobante_activo,
            ))

        return DelegadoCandidatasResult(
            delegado=delegado_dto,
            candidatas=candidatas_list,
            total=len(candidatas_list)
        )

    def list_tipos_liquidacion_proceso(self) -> list:
        """
        Returns all TipoLiquidacion objects for the select dropdown.
        """
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
        return list(TipoLiquidacion.objects.all().order_by("nombre"))

    def list_operatividades_vigentes_delegado_proceso(
        self,
        cip: str,
    ) -> DelegadoOperatividadesVigentesResult:
        """
        Returns all vigentes DelegadoOperacion for a delegado identified by CIP.
        Includes municipalidad, tipo_liquidacion, especialidad and vigencia period info.

        Raises 404 if no delegado found with that CIP.
        """
        from modules.liquidaciones.domain.models.delegado import Delegado

        delegado = Delegado.objects.select_related(
            "perfil_ingeniero"
        ).filter(perfil_ingeniero__cip=cip).first()

        if not delegado:
            raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")

        today = date.today()

        # Get all active operations with vigentes periods
        operaciones = self.core_service.get_operatividades_vigentes_delegado(
            delegado=delegado,
            fecha=today,
        )

        operatividades = []
        for op in operaciones:
            # Extract current periodo dates from the prefetched periodos
            current_periodo = None
            for periodo in op.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break

            periodo_inicio = current_periodo.periodo_inicio if current_periodo else None
            periodo_fin = current_periodo.periodo_fin if current_periodo else None

            tipo_liq_id = str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None
            tipo_liq_codigo = op.tipo_liquidacion.codigo if op.tipo_liquidacion else None
            tipo_liq_nombre = op.tipo_liquidacion.nombre if op.tipo_liquidacion else None

            operatividades.append(DelegadoOperacionVigenteResult(
                id=str(op.id),
                municipalidad_id=str(op.municipalidad_id),
                municipalidad_nombre=op.municipalidad.nombre,
                tipo_liquidacion_id=tipo_liq_id,
                tipo_liquidacion_codigo=tipo_liq_codigo,
                tipo_liquidacion_nombre=tipo_liq_nombre,
                especialidad_id=str(op.especialidad_revision_id),
                especialidad_nombre=op.especialidad_revision.nombre,
                tipo=op.tipo,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            ))

        return DelegadoOperatividadesVigentesResult(
            delegado_id=str(delegado.id),
            cip=delegado.perfil_ingeniero.cip or "",
            nombre_completo=delegado.perfil_ingeniero.nombre_completo,
            operatividades=operatividades,
        )

