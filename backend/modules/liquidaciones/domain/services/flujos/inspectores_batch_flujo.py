"""Flujo transaccional para batch de LiquidacionInspector."""

import uuid

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject

from core.services.related_batch import BatchPayload, BatchUpdateItem, process_batch_payload
from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import (
    LiquidacionInspectorCore,
    liquidacion_inspector_core,
)
from modules.liquidaciones.presentation.schemas.inspectores_batch_schemas import (
    InspectorBasicOut,
    LiquidacionInspectorBatchOut,
    LiquidacionInspectorCreateIn,
    LiquidacionInspectorOut,
    LiquidacionInspectorUpdateIn,
)


class InspectoresBatchFlow:
    @inject
    def __init__(self, core: LiquidacionInspectorCore = None):
        self._core = core or liquidacion_inspector_core

    async def procesar_batch_inspectores(self, liquidacion_id: uuid.UUID, payload) -> LiquidacionInspectorBatchOut:
        batch_payload = BatchPayload[uuid.UUID, LiquidacionInspectorCreateIn, LiquidacionInspectorUpdateIn](
            create=payload.create,
            update=[BatchUpdateItem(id=item.inspector_id, body=item.body) for item in payload.update],
            delete=[item.inspector_id for item in payload.delete],
        )

        def _run_batch():
            with transaction.atomic():
                def create_fn(body: LiquidacionInspectorCreateIn):
                    return self._core._crear_asociacion(
                        liquidacion_id=liquidacion_id,
                        inspector_id=body.inspector_id,
                        periodo=body.periodo,
                        dictamen_revision=body.dictamen_revision,
                        fecha_presentacion=body.fecha_presentacion,
                        fecha_revision=body.fecha_revision,
                    )

                def update_fn(id_: uuid.UUID, body: LiquidacionInspectorUpdateIn):
                    return self._core._actualizar_asociacion(
                        liquidacion_id=liquidacion_id,
                        inspector_id=id_,
                        periodo=body.periodo,
                        dictamen_revision=body.dictamen_revision,
                        fecha_presentacion=body.fecha_presentacion,
                        fecha_revision=body.fecha_revision,
                    )

                def delete_fn(id_: uuid.UUID) -> uuid.UUID:
                    self._core._eliminar_asociacion(liquidacion_id=liquidacion_id, inspector_id=id_)
                    return id_

                result = process_batch_payload(
                    payload=batch_payload,
                    create_fn=create_fn,
                    update_fn=update_fn,
                    delete_fn=delete_fn,
                )

                created_out = []
                for asoc in result.created:
                    fresh = self._core._obtener_asociacion(liquidacion_id, asoc.inspector_id)
                    if fresh:
                        created_out.append(self._map_asociacion_to_out(fresh))

                updated_out = []
                for asoc in result.updated:
                    fresh = self._core._obtener_asociacion(liquidacion_id, asoc.inspector_id)
                    if fresh:
                        updated_out.append(self._map_asociacion_to_out(fresh))

                return LiquidacionInspectorBatchOut(
                    created=created_out,
                    updated=updated_out,
                    deleted=[str(d) for d in result.deleted],
                )

        return await sync_to_async(_run_batch, thread_sensitive=True)()

    def _map_asociacion_to_out(self, asociacion) -> LiquidacionInspectorOut:
        inspector = asociacion.inspector
        perfil = getattr(inspector, "perfil_ingeniero", None)
        especialidad = getattr(inspector, "especialidad", None)
        inspector_basic = InspectorBasicOut(
            id=inspector.id,
            perfil_ingeniero_id=perfil.id if perfil else None,
            perfil_ingeniero_nombres=perfil.nombres if perfil else None,
            perfil_ingeniero_apellidos=(f"{perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip() or None) if perfil else None,
            perfil_ingeniero_cip=perfil.cip if perfil else None,
            especialidad_id=especialidad.id if especialidad else None,
            especialidad_nombre=especialidad.nombre if especialidad else None,
            tipo_liquidacion=inspector.tipo_liquidacion,
            categoria=inspector.categoria,
            numero_registro=inspector.numero_registro,
            vigencia=inspector.vigencia,
        )
        return LiquidacionInspectorOut(
            id=asociacion.id,
            inspector_id=asociacion.inspector_id,
            periodo=asociacion.periodo,
            dictamen_revision=asociacion.dictamen_revision,
            fecha_presentacion=asociacion.fecha_presentacion,
            fecha_revision=asociacion.fecha_revision,
            inspector=inspector_basic,
        )


inspectores_batch_flow = InspectoresBatchFlow()
