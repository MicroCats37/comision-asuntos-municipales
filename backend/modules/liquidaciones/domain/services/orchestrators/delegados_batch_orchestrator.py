"""
DelegadosBatchOrchestrator — business rules for delegados vigentes y batch de liquidaciones.

Validates input, raises HttpError, calls Core for ORM operations and the Flujo
for atomic batch execution. Builds domain Results from ORM objects.
"""
import uuid
from datetime import date
from typing import List, Optional

from injector import inject
from ninja.errors import HttpError

from core.services.related_batch import (
    BatchPayload,
    BatchProcessResult,
    BatchUpdateItem,
)
from modules.liquidaciones.domain.constants import normalizar_tipo_liquidacion
from modules.liquidaciones.domain.results.delegado.delegado_result import (
    DelegadoVigenteResult,
    DelegadosVigentesResult,
    EspecialidadRevisionResult,
    LiquidacionDelegadoBatchResult,
    LiquidacionDelegadoResult,
    LiquidacionDelegadoLiquidacionMinimal,
    LiquidacionDelegadoDelegadoMinimal,
    TipoLiquidacionMinimalResult,
)
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.domain.services.flujos.delegados_batch_flujo import (
    DelegadosBatchFlujo,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    LiquidacionDelegadoBatchIn,
)


class DelegadosBatchOrchestrator:
    """
    Orchestrator for delegados vigentes and LiquidacionDelegado batch endpoints.

    Responsibilities:
    - Input validation (raises HttpError)
    - Calls Core for ORM operations
    - Calls Flujo for atomic batch execution
    - Builds Domain Results from ORM objects
    """

    @inject
    def __init__(
        self,
        core_service: DelegadoCoreService,
        flujo: DelegadosBatchFlujo,
    ):
        self.core_service = core_service
        self.flujo = flujo

    def obtener_delegados_vigentes_proceso(
        self,
        municipalidad_id: uuid.UUID,
        tipo_liquidacion: str,
        revision_id: Optional[uuid.UUID] = None,
    ) -> DelegadosVigentesResult:
        """
        Returns delegados vigentes for a municipalidad + tipo_liquidacion.

        Match:
        1. DelegadoMunicipalidad with municipalidad_id AND
           (liquidacion_revision IS NULL OR matches the tipo)
        2. delegado.especialidad_revision IN especialidades vigentes del tipo
        3. periodo municipal vigente

        revision_id is accepted for frontend compatibility but does not
        participate in the match (already covered by tipo_liquidacion).
        """
        tipo_codigo = normalizar_tipo_liquidacion(tipo_liquidacion)
        today = date.today()

        asignaciones = self.core_service.list_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            tipo_codigo=tipo_codigo,
            fecha=today,
        )

        delegados: list[DelegadoVigenteResult] = []
        for asignacion in asignaciones:
            delegado = asignacion.delegado
            especialidad = delegado.especialidad_revision
            delegados.append(
                DelegadoVigenteResult(
                    id=str(delegado.id),
                    nombre_completo=delegado.perfil_ingeniero.nombre_completo,
                    cip=delegado.perfil_ingeniero.cip or "",
                    especialidad=EspecialidadRevisionResult(
                        id=str(especialidad.id),
                        nombre=especialidad.nombre,
                    ),
                    tipo=asignacion.tipo or "",
                )
            )

        return DelegadosVigentesResult(delegados=delegados)

    def procesar_batch_delegados_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload: LiquidacionDelegadoBatchIn,
    ) -> LiquidacionDelegadoBatchResult:
        """
        Validates the batch payload and delegates atomic execution to the Flujo.

        Validations:
        1. Liquidación existe (404)
        2. Delegado existe (404)
        3. especialidad_revision del delegado ∈ especialidades vigentes del tipo (400)
        4. Asignación municipal vigente para la municipalidad de la liquidación (400)
        5. No duplicar asociación existente (400)
        6. Sin delegado_id duplicado dentro del payload (400)
        7. update/delete validan que la asociación exista (400)
        """
        liquidacion = self.core_service.get_liquidacion_general_by_id(liquidacion_id)
        if not liquidacion:
            raise HttpError(404, f"Liquidación '{liquidacion_id}' no encontrada")

        today = date.today()
        tipo_codigo = liquidacion.tipo_liquidacion.codigo
        especialidad_ids = set(
            self.core_service.list_especialidad_ids_vigentes_para_tipo(
                tipo_codigo, today
            )
        )

        self._validar_delegados_duplicados(payload)

        # Validate creates
        for item in payload.create:
            delegado = self.core_service.get_delegado_by_id(item.delegado_id)
            if not delegado:
                raise HttpError(404, f"Delegado '{item.delegado_id}' no encontrado")
            if (
                delegado.especialidad_revision_id is None
                or str(delegado.especialidad_revision_id) not in especialidad_ids
            ):
                raise HttpError(
                    400,
                    f"El delegado '{item.delegado_id}' no tiene especialidad de "
                    f"revisión vigente para el tipo '{tipo_codigo}'",
                )
            if not self.core_service.get_asignacion_municipal_vigente(
                item.delegado_id,
                liquidacion.municipalidad_id,
                today,
            ):
                raise HttpError(
                    400,
                    f"El delegado '{item.delegado_id}' no tiene asignación "
                    "municipal vigente para la municipalidad de la liquidación",
                )
            if self.core_service.obtener_liquidacion_delegado(liquidacion, delegado):
                raise HttpError(
                    400,
                    f"El delegado '{item.delegado_id}' ya está asociado a la liquidación",
                )

        # Validate updates
        for item in payload.update:
            delegado = self.core_service.get_delegado_by_id(item.delegado_id)
            if not delegado:
                raise HttpError(404, f"Delegado '{item.delegado_id}' no encontrado")
            if not self.core_service.obtener_liquidacion_delegado(liquidacion, delegado):
                raise HttpError(
                    400,
                    f"No existe asociación del delegado '{item.delegado_id}' con la liquidación",
                )

        # Validate deletes
        for item in payload.delete:
            delegado = self.core_service.get_delegado_by_id(item.delegado_id)
            if not delegado:
                raise HttpError(404, f"Delegado '{item.delegado_id}' no encontrado")
            if not self.core_service.obtener_liquidacion_delegado(liquidacion, delegado):
                raise HttpError(
                    400,
                    f"No existe asociación del delegado '{item.delegado_id}' con la liquidación",
                )

        batch = BatchPayload(
            create=[item for item in payload.create],
            update=[
                BatchUpdateItem(id=item.delegado_id, body=item)
                for item in payload.update
            ],
            delete=[item.delegado_id for item in payload.delete],
        )

        batch_result: BatchProcessResult = self.flujo.ejecutar_batch(liquidacion, batch)

        return LiquidacionDelegadoBatchResult(
            created=[
                self._build_liquidacion_delegado_result(ld)
                for ld in batch_result.created
            ],
            updated=[
                self._build_liquidacion_delegado_result(ld)
                for ld in batch_result.updated
            ],
            deleted=batch_result.deleted,
        )

    def _validar_delegados_duplicados(self, payload: LiquidacionDelegadoBatchIn) -> None:
        """Raises HttpError if a delegado_id appears more than once in the payload."""
        delegado_ids = (
            [str(item.delegado_id) for item in payload.create]
            + [str(item.delegado_id) for item in payload.update]
            + [str(item.delegado_id) for item in payload.delete]
        )
        duplicados = {
            delegado_id
            for delegado_id in delegado_ids
            if delegado_ids.count(delegado_id) > 1
        }
        if duplicados:
            raise HttpError(
                400,
                "Delegado(s) duplicado(s) en el payload: "
                + ", ".join(sorted(duplicados)),
            )

    def _build_liquidacion_delegado_result(self, ld) -> LiquidacionDelegadoResult:
        """
        Builds LiquidacionDelegadoResult from a LiquidacionDelegado ORM object.
        Tries to populate nested liquidacion/delegado when relations are loaded
        (select_related), with graceful fallback when they are not.
        """
        try:
            liquidacion_rel = ld.liquidacion
            liquidacion_nested = LiquidacionDelegadoLiquidacionMinimal(
                id=str(liquidacion_rel.id),
                expediente=liquidacion_rel.expediente,
                numero_revision=liquidacion_rel.numero_revision,
                sub_total=float(liquidacion_rel.sub_total) if liquidacion_rel.sub_total else None,
                total=float(liquidacion_rel.total) if liquidacion_rel.total else None,
                municipalidad_nombre=(
                    liquidacion_rel.municipalidad.nombre
                    if hasattr(liquidacion_rel, 'municipalidad') and liquidacion_rel.municipalidad
                    else None
                ),
                proyecto_denominacion=(
                    liquidacion_rel.proyecto.denominacion
                    if hasattr(liquidacion_rel, 'proyecto') and liquidacion_rel.proyecto
                    else None
                ),
                tipo_liquidacion=(
                    TipoLiquidacionMinimalResult(
                        codigo=liquidacion_rel.tipo_liquidacion.codigo,
                        nombre=liquidacion_rel.tipo_liquidacion.nombre,
                    )
                    if hasattr(liquidacion_rel, 'tipo_liquidacion') and liquidacion_rel.tipo_liquidacion
                    else None
                ),
            )
        except Exception:
            liquidacion_nested = None

        try:
            delegado_rel = ld.delegado
            liquidacion_delegado_delegado = LiquidacionDelegadoDelegadoMinimal(
                id=str(delegado_rel.id),
                cip=(
                    delegado_rel.perfil_ingeniero.cip
                    if hasattr(delegado_rel, 'perfil_ingeniero') and delegado_rel.perfil_ingeniero
                    else ""
                ),
                dni=(
                    delegado_rel.perfil_ingeniero.dni
                    if hasattr(delegado_rel, 'perfil_ingeniero') and delegado_rel.perfil_ingeniero
                    else ""
                ),
                nombre_completo=(
                    delegado_rel.perfil_ingeniero.nombre_completo
                    if hasattr(delegado_rel, 'perfil_ingeniero') and delegado_rel.perfil_ingeniero
                    else ""
                ),
            )
        except Exception:
            liquidacion_delegado_delegado = None

        return LiquidacionDelegadoResult(
            id=str(ld.id),
            liquidacion_id=str(ld.liquidacion_id),
            delegado_id=str(ld.delegado_id),
            especialidad_revision=EspecialidadRevisionResult(
                id=str(ld.especialidad_revision.id),
                nombre=ld.especialidad_revision.nombre,
            ),
            liquidacion=liquidacion_nested,
            delegado=liquidacion_delegado_delegado,
            periodo=ld.periodo,
            dictamen_revision=ld.dictamen_revision,
            fecha_presentacion=ld.fecha_presentacion,
            fecha_revision=ld.fecha_revision,
        )

    def listar_asignaciones_proceso(
        self,
        page: int,
        page_size: int,
        cip: Optional[str] = None,
        liquidacion_id: Optional[uuid.UUID] = None,
    ) -> tuple:
        """
        Returns (list[LiquidacionDelegadoResult], total) for the paginated
        GET /liquidaciones/delegados-asignaciones endpoint.

        Relations (liquidacion, delegado, especialidad_revision) are loaded via
        select_related in the core service to avoid N+1.
        """
        objects, total = self.core_service.list_liquidacion_delegado_paginated(
            page=page,
            page_size=page_size,
            cip=cip,
            liquidacion_id=liquidacion_id,
        )
        results: List[LiquidacionDelegadoResult] = [
            self._build_liquidacion_delegado_result(ld) for ld in objects
        ]
        return results, total
