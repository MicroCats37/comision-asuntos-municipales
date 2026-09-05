"""
InspectoresBatchOrchestrator — business rules for LiquidacionInspector batch operations.

Validates input, raises HttpError, calls Core for ORM operations and the Flujo
for atomic batch execution. Builds domain Results from ORM objects.
"""
import uuid
from typing import List, Optional

from injector import inject
from ninja.errors import HttpError

from core.services.related_batch import (
    BatchPayload,
    BatchProcessResult,
    BatchUpdateItem,
)
from modules.liquidaciones.domain.services.core.inspector.inspector_core_service import (
    InspectorCoreService,
)
from modules.liquidaciones.domain.services.flujos.inspectores_batch_flujo import (
    InspectoresBatchFlujo,
)
from modules.liquidaciones.presentation.schemas.inspector.inspector_batch_schemas import (
    LiquidacionInspectorBatchIn,
    LiquidacionInspectorOut,
)


class InspectoresBatchOrchestrator:
    """
    Orchestrator for LiquidacionInspector batch endpoints.

    Responsibilities:
    - Input validation (raises HttpError)
    - Calls Core for ORM operations
    - Calls Flujo for atomic batch execution
    - Builds Domain Results from ORM objects
    """

    @inject
    def __init__(
        self,
        core_service: InspectorCoreService,
        flujo: InspectoresBatchFlujo,
    ):
        self.core_service = core_service
        self.flujo = flujo

    def procesar_batch_inspectores_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload: LiquidacionInspectorBatchIn,
    ) -> dict:
        """
        Validates the batch payload and delegates atomic execution to the Flujo.

        Validations:
        1. Liquidación existe (404)
        2. inspector_id existe (404)
        3. inspector_operacion_id existe y pertenece al inspector_id (400)
        4. No duplicar asociación existente (400)
        5. Sin inspector_id duplicado dentro del payload (400)
        6. delete validan que la asociación exista (400)
        """
        liquidacion = self.core_service.get_liquidacion_general_by_id(liquidacion_id)
        if not liquidacion:
            raise HttpError(404, f"Liquidación '{liquidacion_id}' no encontrada")

        self._validar_inspectores_duplicados(payload)

        # Validate creates
        for item in payload.create:
            inspector = self.core_service.get_inspector_by_id(item.inspector_id)
            if not inspector:
                raise HttpError(404, f"Inspector '{item.inspector_id}' no encontrado")

            inspector_operacion = self.core_service.get_inspector_operacion_by_id(
                item.inspector_operacion_id
            )
            if not inspector_operacion:
                raise HttpError(
                    404,
                    f"InspectorOperacion '{item.inspector_operacion_id}' no encontrado",
                )

            # Validate inspector_operacion belongs to inspector
            if str(inspector_operacion.inspector_id) != str(item.inspector_id):
                raise HttpError(
                    400,
                    f"InspectorOperacion '{item.inspector_operacion_id}' no pertenece "
                    f"al inspector '{item.inspector_id}'",
                )

            # Check no duplicate association
            existing = self.core_service.obtener_liquidacion_inspector(
                liquidacion=liquidacion,
                inspector=inspector,
            )
            if existing:
                raise HttpError(
                    400,
                    f"El inspector '{item.inspector_id}' ya está asociado a la liquidación",
                )

        # Validate deletes
        for item in payload.delete:
            inspector = self.core_service.get_inspector_by_id(item.inspector_id)
            if not inspector:
                raise HttpError(404, f"Inspector '{item.inspector_id}' no encontrado")

            existing = self.core_service.obtener_liquidacion_inspector(
                liquidacion=liquidacion,
                inspector=inspector,
            )
            if not existing:
                raise HttpError(
                    400,
                    f"No existe asociación del inspector '{item.inspector_id}' "
                    "con la liquidación",
                )

        # Get the liquidacion tipo (LiquidacionPorCategoriaVisitas for IO)
        # The liquidacion_id from URL is the LiquidacionPorCategoriaVisitas id
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_visitas import (
            LiquidacionPorCategoriaVisitas,
        )
        liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.filter(
            id=liquidacion_id
        ).first()
        if not liquidacion_visitas:
            # Try by liquidacion_general_id
            liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.filter(
                liquidacion_id=liquidacion_id
            ).first()

        batch = BatchPayload(
            create=[item for item in payload.create],
            update=[
                BatchUpdateItem(id=item.inspector_id, body=item)
                for item in payload.update
            ],
            delete=[item.inspector_id for item in payload.delete],
        )

        batch_result: BatchProcessResult = self.flujo.ejecutar_batch(
            liquidacion_visitas or liquidacion, batch
        )

        return {
            "created": [
                self._build_liquidacion_inspector_result(li)
                for li in batch_result.created
            ],
            "updated": [
                self._build_liquidacion_inspector_result(li)
                for li in batch_result.updated
            ],
            "deleted": batch_result.deleted,
        }

    def _validar_inspectores_duplicados(
        self, payload: LiquidacionInspectorBatchIn
    ) -> None:
        """Raises HttpError if an inspector_id appears more than once in the payload."""
        inspector_ids = (
            [str(item.inspector_id) for item in payload.create]
            + [str(item.inspector_id) for item in payload.update]
            + [str(item.inspector_id) for item in payload.delete]
        )
        duplicados = {
            inspector_id
            for inspector_id in inspector_ids
            if inspector_ids.count(inspector_id) > 1
        }
        if duplicados:
            raise HttpError(
                400,
                "Inspector(es) duplicado(s) en el payload: "
                + ", ".join(sorted(duplicados)),
            )

    def _build_liquidacion_inspector_result(
        self, li
    ) -> LiquidacionInspectorOut:
        """
        Builds LiquidacionInspectorOut from a LiquidacionInspector ORM object.
        """
        return LiquidacionInspectorOut(
            id=li.id,
            liquidacion_id=li.liquidacion_id,
            inspector_id=li.inspector_id,
            inspector_operacion_id=(
                li.inspector_operacion_id if li.inspector_operacion else None
            ),
        )

    def get_liquidacion_general_by_id(self, liquidacion_id: uuid.UUID):
        """Proxy to general core service for liquidacion lookup."""
        from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
            LiquidacionGeneralCoreService,
        )
        core = LiquidacionGeneralCoreService()
        return core.get_liquidacion_general_by_id(liquidacion_id)
