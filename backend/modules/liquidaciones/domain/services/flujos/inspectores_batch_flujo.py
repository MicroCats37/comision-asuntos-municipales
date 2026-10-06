"""
InspectoresBatchFlujo — atomic batch operations for LiquidacionInspector.

@transaction.atomic coordination of ORM operations via InspectorCoreService.
NO validation, NO business logic — trusts the Orchestrator.
"""
from uuid import UUID

from django.db import transaction
from injector import inject

from core.services.related_batch import (
    BatchPayload,
    BatchProcessResult,
    process_batch_payload,
)
from modules.liquidaciones.domain.services.core.inspector.inspector_core_service import (
    InspectorCoreService,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_batch_schemas import (
    LiquidacionInspectorCreateIn,
    LiquidacionInspectorUpdateIn,
)


class InspectoresBatchFlujo:
    """
    Flujo for LiquidacionInspector batch operations.

    Applies create/update/delete within a single transaction via
    related_batch.process_batch_payload. Any failure rolls back everything.
    """

    @inject
    def __init__(
        self,
        core_service: InspectorCoreService,
    ):
        self.core_service = core_service

    def ejecutar_batch(
        self,
        liquidacion,
        payload: BatchPayload[UUID, LiquidacionInspectorCreateIn, LiquidacionInspectorUpdateIn],
    ) -> BatchProcessResult:
        """Runs the batch inside @transaction.atomic."""
        return self._ejecutar_batch_sync(liquidacion, payload)

    @transaction.atomic()
    def _ejecutar_batch_sync(
        self,
        liquidacion,
        payload: BatchPayload[UUID, LiquidacionInspectorCreateIn, LiquidacionInspectorUpdateIn],
    ) -> BatchProcessResult:
        def create_fn(body: LiquidacionInspectorCreateIn):
            inspector_operacion = self.core_service.get_inspector_operacion_by_id(
                body.inspector_operacion_id
            )
            return self.core_service.crear_liquidacion_inspector(
                liquidacion=liquidacion,
                inspector_id=body.inspector_id,
                inspector_operacion=inspector_operacion,
            )

        def update_fn(id_: UUID, body: LiquidacionInspectorUpdateIn):
            # Update not supported for LiquidacionInspector — just re-fetch
            return self.core_service.get_liquidacion_inspector_by_ids(
                liquidacion_id=str(liquidacion.id),
                inspector_id=str(id_),
            )

        def delete_fn(id_: UUID) -> str:
            self.core_service.eliminar_liquidacion_inspector(
                liquidacion=liquidacion,
                inspector_id=id_,
            )
            return str(id_)

        return process_batch_payload(
            payload=payload,
            create_fn=create_fn,
            update_fn=update_fn,
            delete_fn=delete_fn,
        )
