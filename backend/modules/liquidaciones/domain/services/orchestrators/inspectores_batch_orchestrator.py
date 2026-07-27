"""Orchestrator para reglas de negocio del batch de inspectores."""

import uuid

from asgiref.sync import sync_to_async
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import (
    LiquidacionInspectorCore,
    liquidacion_inspector_core,
)
from modules.liquidaciones.domain.services.flujos.inspectores_batch_flujo import (
    InspectoresBatchFlow,
    inspectores_batch_flow,
)
from modules.liquidaciones.presentation.schemas.inspectores_batch_schemas import (
    LiquidacionInspectorBatchIn,
    LiquidacionInspectorBatchOut,
)


class InspectoresBatchOrchestrator:
    @inject
    def __init__(self, core: LiquidacionInspectorCore = None, flow: InspectoresBatchFlow = None):
        self._core = core or liquidacion_inspector_core
        self._flow = flow or inspectores_batch_flow

    async def procesar_batch_inspectores(
        self,
        liquidacion_id: uuid.UUID,
        payload: LiquidacionInspectorBatchIn,
    ) -> LiquidacionInspectorBatchOut:
        liquidacion = await sync_to_async(self._core._obtener_liquidacion_por_id)(liquidacion_id)
        if not liquidacion:
            raise HttpError(404, f"Liquidación con ID '{liquidacion_id}' no encontrada.")

        tipo_previa = await sync_to_async(self._core._obtener_tipo_previa_io)(liquidacion)
        if tipo_previa not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            raise HttpError(400, "La liquidación IO no tiene una liquidación previa de Edificación o Habilitación Urbana.")

        self._validar_duplicados_en_payload(payload)
        await self._validar_create(liquidacion_id, payload, tipo_previa)
        await self._validar_update(liquidacion_id, payload)
        await self._validar_delete(liquidacion_id, payload)

        return await self._flow.procesar_batch_inspectores(liquidacion_id=liquidacion_id, payload=payload)

    def _validar_duplicados_en_payload(self, payload: LiquidacionInspectorBatchIn) -> None:
        ids = [item.inspector_id for item in payload.create]
        ids += [item.inspector_id for item in payload.update]
        ids += [item.inspector_id for item in payload.delete]
        if len(ids) != len(set(ids)):
            raise HttpError(400, "Cada inspector_id debe aparecer en una sola operación del batch.")

    async def _validar_create(self, liquidacion_id: uuid.UUID, payload: LiquidacionInspectorBatchIn, tipo_previa: str) -> None:
        for item in payload.create:
            inspector = await sync_to_async(self._core._obtener_inspector_por_id)(item.inspector_id)
            if not inspector:
                raise HttpError(404, f"Inspector con ID '{item.inspector_id}' no encontrado.")

            if not await sync_to_async(self._core._es_inspector_activo)(item.inspector_id):
                raise HttpError(400, f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' no está activo.")

            if not await sync_to_async(self._core._inspector_vigente)(item.inspector_id):
                raise HttpError(400, f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' no está vigente.")

            if not await sync_to_async(self._core._tipo_inspector_compatible)(item.inspector_id, tipo_previa):
                raise HttpError(400, f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' no corresponde al tipo '{tipo_previa}'.")

            if await sync_to_async(self._core._existe_asociacion)(liquidacion_id, item.inspector_id):
                raise HttpError(400, f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' ya está asociado a esta liquidación.")

    async def _validar_update(self, liquidacion_id: uuid.UUID, payload: LiquidacionInspectorBatchIn) -> None:
        for item in payload.update:
            asociacion = await sync_to_async(self._core._obtener_asociacion)(liquidacion_id, item.inspector_id)
            if not asociacion:
                raise HttpError(404, f"El inspector con ID '{item.inspector_id}' no está asociado a esta liquidación.")

    async def _validar_delete(self, liquidacion_id: uuid.UUID, payload: LiquidacionInspectorBatchIn) -> None:
        for item in payload.delete:
            asociacion = await sync_to_async(self._core._obtener_asociacion)(liquidacion_id, item.inspector_id)
            if not asociacion:
                raise HttpError(404, f"El inspector con ID '{item.inspector_id}' no está asociado a esta liquidación.")
