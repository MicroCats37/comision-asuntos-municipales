"""
DelegadosBatchFlujo — Flujo transaccional para batch de LiquidacionDelegado.

Responsabilidades (Fase 4):
    1. Ejecutar operaciones create/update/delete en una transacción atómica.
    2. Usar related_batch.process_batch_payload para enrutar operaciones.
    3. Mapear resultados a LiquidacionDelegadoOut.

Patrón:
    - El flujo recibe el payload ya validado por el orquestador.
    - Usa @transaction.atomic dentro de sync_to_async(thread_sensitive=True).
    - El orquestador (Fase 3) valida, luego llama a este flujo.
    - No valida — solo ejecuta operaciones de ORM via Core.
"""
import uuid
from datetime import date
from typing import Optional

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject

from core.services.related_batch import (
    BatchPayload,
    BatchUpdateItem,
    BatchProcessResult,
    process_batch_payload,
)
from modules.liquidaciones.domain.services.core.liquidacion_delegado_core import (
    LiquidacionDelegadoCore,
    liquidacion_delegado_core,
)
from modules.liquidaciones.presentation.schemas.delegados_batch_schemas import (
    LiquidacionDelegadoCreateIn,
    LiquidacionDelegadoUpdateIn,
    LiquidacionDelegadoDeleteIn,
    LiquidacionDelegadoOut,
    LiquidacionDelegadoBatchOut,
    DelegadoBasicOut,
)


class DelegadosBatchFlow:
    """
    Flujo transaccional para operaciones batch de LiquidacionDelegado.

    Ejecuta create/update/delete en una sola transacción atómica.
    El orquestador valida primero, luego delega aquí para la ejecución.
    """

    @inject
    def __init__(self, core: LiquidacionDelegadoCore = None):
        self._core = core or liquidacion_delegado_core

    async def procesar_batch_delegados(
        self,
        liquidacion_id: uuid.UUID,
        payload: "LiquidacionDelegadoBatchIn",  # Forward ref to avoid circular
    ) -> LiquidacionDelegadoBatchOut:
        """
        Procesa un batch de operaciones create/update/delete de delegados.

        Ejecuta todas las operaciones dentro de una transacción atómica.
        Si cualquier operación falla, se hace rollback completo.

        Args:
            liquidacion_id: UUID de la liquidación objetivo.
            payload: Payload batch con create/update/delete.

        Returns:
            LiquidacionDelegadoBatchOut con resultados de cada operación.

        Raises:
            Cualquier excepción de ORM — se propaga para rollback.
        """
        # Preparar el payload para process_batch_payload
        # El payload de entrada usa LiquidacionDelegadoUpdateItemIn que tiene
        # delegado_id + body, pero process_batch_payload espera BatchUpdateItem[id, body]
        batch_payload = BatchPayload[uuid.UUID, LiquidacionDelegadoCreateIn, LiquidacionDelegadoUpdateIn](
            create=payload.create,
            update=[
                BatchUpdateItem(id=item.delegado_id, body=item.body)
                for item in payload.update
            ],
            delete=[item.delegado_id for item in payload.delete],
        )

        # Ejecutar dentro de transacción atómica
        # Usamos closure para capturar liquidacion_id y pasar a los callbacks
        def _run_batch():
            with transaction.atomic():
                # Crear callbacks con closure para capturar liquidacion_id
                def create_fn(body: LiquidacionDelegadoCreateIn):
                    return self._core._crear_asociacion(
                        liquidacion_id=liquidacion_id,
                        delegado_id=body.delegado_id,
                        periodo=body.periodo,
                        dictamen_revision=body.dictamen_revision,
                        fecha_presentacion=body.fecha_presentacion,
                        fecha_revision=body.fecha_revision,
                    )

                def update_fn(id_: uuid.UUID, body: LiquidacionDelegadoUpdateIn):
                    return self._core._actualizar_asociacion(
                        liquidacion_id=liquidacion_id,
                        delegado_id=id_,
                        periodo=body.periodo,
                        dictamen_revision=body.dictamen_revision,
                        fecha_presentacion=body.fecha_presentacion,
                        fecha_revision=body.fecha_revision,
                    )

                def delete_fn(id_: uuid.UUID) -> uuid.UUID:
                    self._core._eliminar_asociacion(
                        liquidacion_id=liquidacion_id,
                        delegado_id=id_,
                    )
                    return id_

                result = process_batch_payload(
                    payload=batch_payload,
                    create_fn=create_fn,
                    update_fn=update_fn,
                    delete_fn=delete_fn,
                )

                # Mapear resultados a LiquidacionDelegadoOut
                # NOTE: process_batch_payload re-fetched the associations in callbacks
                # so we need to get fresh data for mapping
                # We re-fetch by liquidacion_id + delegado_id since we only have IDs

                created_out = []
                for asoc in result.created:
                    # Re-fetch with related data for mapping
                    fresh = self._core._obtener_asociacion(liquidacion_id, asoc.delegado_id)
                    if fresh:
                        created_out.append(self._map_asociacion_to_out(fresh))

                updated_out = []
                for asoc in result.updated:
                    fresh = self._core._obtener_asociacion(liquidacion_id, asoc.delegado_id)
                    if fresh:
                        updated_out.append(self._map_asociacion_to_out(fresh))

                deleted_ids = result.deleted

                return LiquidacionDelegadoBatchOut(
                    created=created_out,
                    updated=updated_out,
                    deleted=[str(d) for d in deleted_ids],
                )

        return await sync_to_async(_run_batch, thread_sensitive=True)()

    # -------------------------------------------------------------------------
    # Mapping a schemas de salida
    # -------------------------------------------------------------------------

    def _map_asociacion_to_out(
        self,
        asociacion: "LiquidacionDelegado",
    ) -> LiquidacionDelegadoOut:
        """
        Mapea una instancia LiquidacionDelegado a LiquidacionDelegadoOut.

        Args:
            asociacion: Instancia ORM de LiquidacionDelegado.

        Returns:
            LiquidacionDelegadoOut con datos de la asociación y delegado.
        """
        # Obtener delegado con relaciones preload (ya deben estar en el objeto)
        delegado = asociacion.delegado

        # Mapear información básica del delegado
        perfil_ingeniero = getattr(delegado, 'perfil_ingeniero', None)
        especialidad = getattr(delegado, 'especialidad', None)

        delegado_basic = None
        if delegado:
            perfil_ingeniero_nombres = None
            perfil_ingeniero_apellidos = None
            perfil_ingeniero_cip = None

            if perfil_ingeniero:
                perfil_ingeniero_nombres = getattr(perfil_ingeniero, 'nombres', None)
                perfil_ingeniero_apellidos = getattr(perfil_ingeniero, 'apellido_paterno', None)
                # CIP podría estar en otro campo o no existir
                perfil_ingeniero_cip = getattr(perfil_ingeniero, 'cip', None)

            especialidad_id = None
            especialidad_nombre = None
            if especialidad:
                especialidad_id = getattr(especialidad, 'id', None)
                especialidad_nombre = getattr(especialidad, 'nombre', None)

            # Tipo de delegado (titular/alterno)
            tipo_delegado = getattr(delegado, 'tipo', None)

            delegado_basic = DelegadoBasicOut(
                id=delegado.id,
                perfil_ingeniero_id=perfil_ingeniero.id if perfil_ingeniero else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=especialidad_id,
                especialidad_nombre=especialidad_nombre,
                tipo=tipo_delegado,
            )

        return LiquidacionDelegadoOut(
            id=asociacion.id,
            delegado_id=asociacion.delegado_id,
            periodo=asociacion.periodo,
            dictamen_revision=asociacion.dictamen_revision,
            fecha_presentacion=asociacion.fecha_presentacion,
            fecha_revision=asociacion.fecha_revision,
            delegado=delegado_basic,
        )


# Instancia singleton
delegados_batch_flow = DelegadosBatchFlow()
