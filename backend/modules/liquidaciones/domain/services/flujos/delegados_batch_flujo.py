"""
DelegadosBatchFlujo — atomic batch operations for LiquidacionDelegado.

@transaction.atomic coordination of ORM operations via DelegadoCoreService.
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
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
    LiquidacionDelegadoCreateIn,
    LiquidacionDelegadoUpdateIn,
)


class DelegadosBatchFlujo:
    """
    Flujo for LiquidacionDelegado batch operations.

    Applies create/update/delete within a single transaction via
    related_batch.process_batch_payload. Any failure rolls back everything.
    """

    @inject
    def __init__(
        self,
        core_service: DelegadoCoreService,
    ):
        self.core_service = core_service

    def ejecutar_batch(
        self,
        liquidacion,
        payload: BatchPayload[UUID, LiquidacionDelegadoCreateIn, LiquidacionDelegadoUpdateIn],
    ) -> BatchProcessResult:
        """Runs the batch inside @transaction.atomic."""
        return self._ejecutar_batch_sync(liquidacion, payload)

    @transaction.atomic()
    def _ejecutar_batch_sync(
        self,
        liquidacion,
        payload: BatchPayload[UUID, LiquidacionDelegadoCreateIn, LiquidacionDelegadoUpdateIn],
    ) -> BatchProcessResult:
        def create_fn(body: LiquidacionDelegadoCreateIn):
            delegado = self.core_service.get_delegado_by_id(body.delegado_id)
            # La especialidad ahora se resuelve desde la operación vigente del delegado
            # para la municipalidad + tipo de la liquidación.
            operacion = self.core_service.get_operacion_vigente_para_liquidacion(
                delegado=delegado,
                liquidacion=liquidacion,
            )
            especialidad_revision = operacion.especialidad_revision if operacion else None
            return self.core_service.crear_liquidacion_delegado(
                liquidacion=liquidacion,
                delegado=delegado,
                especialidad_revision=especialidad_revision,
            )

        def update_fn(id_: UUID, body: LiquidacionDelegadoUpdateIn):
            delegado = self.core_service.get_delegado_by_id(id_)
            campos = {}
            if body.periodo is not None:
                campos["periodo"] = body.periodo
            if body.dictamen_revision is not None:
                campos["dictamen_revision"] = body.dictamen_revision
            if body.fecha_presentacion is not None:
                campos["fecha_presentacion"] = body.fecha_presentacion
            if body.fecha_revision is not None:
                campos["fecha_revision"] = body.fecha_revision
            return self.core_service.actualizar_liquidacion_delegado(
                liquidacion=liquidacion,
                delegado=delegado,
                **campos,
            )

        def delete_fn(id_: UUID) -> str:
            delegado = self.core_service.get_delegado_by_id(id_)
            self.core_service.eliminar_liquidacion_delegado(
                liquidacion=liquidacion,
                delegado=delegado,
            )
            return str(id_)

        return process_batch_payload(
            payload=payload,
            create_fn=create_fn,
            update_fn=update_fn,
            delete_fn=delete_fn,
        )
