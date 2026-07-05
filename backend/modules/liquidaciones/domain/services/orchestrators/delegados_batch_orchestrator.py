"""
DelegadosBatchOrchestrator — Reglas de negocio para batch de LiquidacionDelegado.

Ubicado en: domain/services/orchestrators/delegados_batch_orchestrator.py

Responsabilidades (Fase 3):
    1. Validar que la liquidación existe.
    2. Validar que cada delegado de create existe y está activo.
    3. Validar que el delegado tiene asignación municipal activa para la municipalidad
       de la liquidación.
    4. Validar que el delegado tiene periodo vigente.
    5. Validar que la categoría de MunicipalidadDelegado es compatible con
       tipo_liquidacion de la liquidación.
    6. Validar que create no duplica delegado en la misma liquidación.
    7. Validar que update/delete pertenecen a la liquidación por delegado_id.
    8. Validar duplicados dentro del payload (entre create/update/delete).

Patrón:
    - Orchestrator recibe el payload batch, valida, y delega a Core/Flujo.
    - HttpError(400) para errores de negocio, HttpError(404) para no encontrado.
    - Método público: procesar_batch_delegados (async).

NO expõe endpoint aún — eso es Fase 5.
"""
import uuid
from typing import Optional

from injector import inject
from ninja.errors import HttpError
from asgiref.sync import sync_to_async

from modules.liquidaciones.domain.services.core.liquidacion_delegado_core import (
    LiquidacionDelegadoCore,
    liquidacion_delegado_core,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_edificaciones_orchestrator import (
    LiquidacionesEdificacionesOrchestrator,
)
from modules.liquidaciones.domain.services.flows.delegados_batch_flujo import (
    DelegadosBatchFlow,
    delegados_batch_flow,
)
from modules.liquidaciones.presentation.schemas.delegados_batch_schemas import (
    LiquidacionDelegadoBatchIn,
    LiquidacionDelegadoCreateIn,
    LiquidacionDelegadoUpdateItemIn,
    LiquidacionDelegadoDeleteIn,
    LiquidacionDelegadoBatchOut,
)
from modules.liquidaciones.domain.constants import DelegadoStatus


class DelegadosBatchOrchestrator:
    """
    Orchestrator para operaciones batch de LiquidacionDelegado.

    Valida todas las reglas de negocio antes de permitir que el flujo
    (Fase 4) ejecute las operaciones en base de datos.

    Inyecta:
        - liquidacion_delegado_core: operaciones de ORM sync
        - delegados_batch_flow: flujo transaccional (Fase 4)
    """

    @inject
    def __init__(
        self,
        core: LiquidacionDelegadoCore = None,
        flow: DelegadosBatchFlow = None,
    ):
        self._core = core or liquidacion_delegado_core
        self._flow = flow or delegados_batch_flow

    # -------------------------------------------------------------------------
    # Método público para Fase 4/5
    # -------------------------------------------------------------------------

    async def procesar_batch_delegados(
        self,
        liquidacion_id: uuid.UUID,
        payload: LiquidacionDelegadoBatchIn,
    ) -> LiquidacionDelegadoBatchOut:
        """
        Valida y procesa un batch payload de liquidacion delegados.

        Este método es el punto de entrada público que Fase 4 (Flujo) y
        Fase 5 (Controller) usarán.

        1. Valida todas las reglas de negocio (Fase 3).
        2. Si todas las validaciones pasan, ejecuta el flujo transaccional (Fase 4).
        3. Retorna los resultados reales.

        Args:
            liquidacion_id: UUID de la liquidación objetivo.
            payload: BatchLiquidacionDelegadoSchema con create/update/delete.

        Returns:
            LiquidacionDelegadoBatchOut con resultados de create/update/delete.

        Raises:
            HttpError(404): Liquidación no encontrada.
            HttpError(400): Violación de regla de negocio.
        """
        # 1. Validar liquidación existe
        liquidacion = await self._validar_liquidacion_existe(liquidacion_id)

        # 2. Recolectar todos los delegado_ids del payload
        all_delegado_ids = self._recolectar_delegado_ids(payload)

        # 3. Validar duplicados dentro del payload
        await self._validar_duplicados_en_payload(payload)

        # 4. Validaciones para operations de CREATE
        await self._validar_operations_create(
            liquidacion_id=liquidacion_id,
            creates=payload.create,
            liquidacion=liquidacion,
        )

        # 5. Validaciones para operations de UPDATE
        await self._validar_operations_update(
            liquidacion_id=liquidacion_id,
            updates=payload.update,
        )

        # 6. Validaciones para operations de DELETE
        await self._validar_operations_delete(
            liquidacion_id=liquidacion_id,
            deletes=payload.delete,
        )

        # 7. Ejecutar flujo transaccional (Fase 4)
        # Si llega aquí, todas las validaciones pasaron
        result = await self._flow.procesar_batch_delegados(
            liquidacion_id=liquidacion_id,
            payload=payload,
        )

        return result

    # -------------------------------------------------------------------------
    # Validaciones de Liquidación
    # -------------------------------------------------------------------------

    async def _validar_liquidacion_existe(
        self,
        liquidacion_id: uuid.UUID,
    ) -> any:
        """
        Valida que la liquidación existe.

        Args:
            liquidacion_id: UUID de la liquidación.

        Returns:
            LiquidacionGeneral si existe.

        Raises:
            HttpError(404): Liquidación no encontrada.
        """
        liquidacion = await sync_to_async(
            self._core._obtener_liquidacion_por_id
        )(liquidacion_id)

        if not liquidacion:
            raise HttpError(
                404,
                f"Liquidación con ID '{liquidacion_id}' no encontrada.",
            )

        return liquidacion

    # -------------------------------------------------------------------------
    # Validaciones de Duplicados en Payload
    # -------------------------------------------------------------------------

    def _recolectar_delegado_ids(
        self,
        payload: LiquidacionDelegadoBatchIn,
    ) -> list[uuid.UUID]:
        """
        Recolecta todos los delegado_ids del payload batch.

        Args:
            payload: Batch payload.

        Returns:
            Lista de delegado_ids presentes en el payload.
        """
        ids: list[uuid.UUID] = []

        for item in payload.create:
            ids.append(item.delegado_id)

        for item in payload.update:
            ids.append(item.delegado_id)

        for item in payload.delete:
            ids.append(item.delegado_id)

        return ids

    def _recolectar_delegado_ids_create(
        self,
        payload: LiquidacionDelegadoBatchIn,
    ) -> list[uuid.UUID]:
        """Recolecta delegado_ids solo de operaciones create."""
        return [item.delegado_id for item in payload.create]

    async def _validar_duplicados_en_payload(
        self,
        payload: LiquidacionDelegadoBatchIn,
    ) -> None:
        """
        Valida que no haya delegado_ids duplicados dentro del payload.

        Un mismo delegado no puede aparecer en más de una operación
        (create+update, create+delete, update+delete, etc.) en el mismo
        batch.

        Raises:
            HttpError(400): Hay duplicados dentro del payload.
        """
        create_ids = set(self._recolectar_delegado_ids_create(payload))
        update_ids = set(item.delegado_id for item in payload.update)
        delete_ids = set(item.delegado_id for item in payload.delete)

        all_ids = list(create_ids) + list(update_ids) + list(delete_ids)
        if len(all_ids) != len(set(all_ids)):
            # Encontrar duplicados
            seen: set[uuid.UUID] = set()
            duplicated: list[uuid.UUID] = []
            for did in all_ids:
                if did in seen:
                    duplicated.append(did)
                seen.add(did)

            raise HttpError(
                400,
                f"Delegado(s) duplicado(s) en el payload batch: {[str(d) for d in duplicated]}. "
                "Cada delegado_id debe aparecer en una sola operación (create, update o delete).",
            )

    # -------------------------------------------------------------------------
    # Validaciones de CREATE
    # -------------------------------------------------------------------------

    async def _validar_operations_create(
        self,
        liquidacion_id: uuid.UUID,
        creates: list[LiquidacionDelegadoCreateIn],
        liquidacion: any,
    ) -> None:
        """
        Valida todas las operaciones de create.

        Para cada delegado en create:
            1. Que exista.
            2. Que esté activo.
            3. Que tenga asignación municipal activa para la municipalidad de la liquidación.
            4. Que la categoría sea compatible con tipo_liquidacion.
            5. Que no exista ya la asociación en la liquidación.

        Args:
            liquidacion_id: UUID de la liquidación.
            creates: Lista de items a crear.
            liquidacion: Instancia de LiquidacionGeneral.

        Raises:
            HttpError(404): Delegado no encontrado.
            HttpError(400): Violación de regla de negocio.
        """
        municipalidad_id = liquidacion.municipalidad_id
        tipo_liquidacion = liquidacion.tipo_liquidacion

        for item in creates:
            delegado_id = item.delegado_id

            # 1. Que el delegado exista
            delegado = await sync_to_async(self._core._obtener_delegado_por_id)(
                delegado_id
            )
            if not delegado:
                raise HttpError(
                    404,
                    f"Delegado con ID '{delegado_id}' no encontrado.",
                )

            # 2. Que esté activo
            activo = await sync_to_async(self._core._es_delegado_activo)(
                delegado_id
            )
            if not activo:
                raise HttpError(
                    400,
                    f"El delegado '{delegado.perfil_ingeniero.nombre_completo}' "
                    f"(ID={delegado_id}) no está activo.",
                )

            # 3. Que tenga asignación municipal activa para la municipalidad de la liquidación
            asignacion = await sync_to_async(self._core._obtener_asignacion_municipal)(
                delegado_id=delegado_id,
                municipalidad_id=municipalidad_id,
            )
            if not asignacion:
                raise HttpError(
                    400,
                    f"El delegado '{delegado.perfil_ingeniero.nombre_completo}' "
                    f"(ID={delegado_id}) no tiene asignación activa para la "
                    f"municipalidad de esta liquidación.",
                )

            # 4. Que la categoría sea compatible con tipo_liquidacion
            categoria_delegado = asignacion.categoria
            categoria_valida = await sync_to_async(
                self._core._verificar_categoria_valida_para_tipo_liquidacion
            )(
                categoria_delegado=categoria_delegado,
                tipo_liquidacion=tipo_liquidacion,
            )
            if not categoria_valida:
                raise HttpError(
                    400,
                    f"La categoría del delegado '{delegado.perfil_ingeniero.nombre_completo}' "
                    f"(ID={delegado_id}) es '{categoria_delegado}', pero no es válida para "
                    f"liquidaciones de tipo '{tipo_liquidacion}'. "
                    f"Categoría esperada para este tipo: "
                    f"'{self._categoria_esperada_por_tipo(tipo_liquidacion)}'.",
                )

            # 5. Que no exista ya la asociación en la liquidación
            existe_asociacion = await sync_to_async(self._core._existe_asociacion)(
                liquidacion_id=liquidacion_id,
                delegado_id=delegado_id,
            )
            if existe_asociacion:
                raise HttpError(
                    400,
                    f"El delegado '{delegado.perfil_ingeniero.nombre_completo}' "
                    f"(ID={delegado_id}) ya está asociado a esta liquidación. "
                    "Use update para modificar sus datos.",
                )

            # 6. Que tenga periodo vigente
            periodo = await sync_to_async(self._core._obtener_periodo_vigente)(
                delegado_id=delegado_id,
            )
            if not periodo:
                raise HttpError(
                    400,
                    f"El delegado '{delegado.perfil_ingeniero.nombre_completo}' "
                    f"(ID={delegado_id}) no tiene un periodo vigente.",
                )

    # -------------------------------------------------------------------------
    # Validaciones de UPDATE
    # -------------------------------------------------------------------------

    async def _validar_operations_update(
        self,
        liquidacion_id: uuid.UUID,
        updates: list[LiquidacionDelegadoUpdateItemIn],
    ) -> None:
        """
        Valida todas las operaciones de update.

        Para cada delegado en update:
            1. Que la asociación exista en la liquidación.

        Args:
            liquidacion_id: UUID de la liquidación.
            updates: Lista de items a actualizar.

        Raises:
            HttpError(404): Asociación no encontrada.
        """
        for item in updates:
            delegado_id = item.delegado_id

            asociacion = await sync_to_async(self._core._obtener_asociacion)(
                liquidacion_id=liquidacion_id,
                delegado_id=delegado_id,
            )
            if not asociacion:
                raise HttpError(
                    404,
                    f"El delegado con ID '{delegado_id}' no está asociado a "
                    f"esta liquidación. No se puede actualizar.",
                )

    # -------------------------------------------------------------------------
    # Validaciones de DELETE
    # -------------------------------------------------------------------------

    async def _validar_operations_delete(
        self,
        liquidacion_id: uuid.UUID,
        deletes: list[LiquidacionDelegadoDeleteIn],
    ) -> None:
        """
        Valida todas las operaciones de delete.

        Para cada delegado en delete:
            1. Que la asociación exista en la liquidación.

        Args:
            liquidacion_id: UUID de la liquidación.
            deletes: Lista de items a eliminar.

        Raises:
            HttpError(404): Asociación no encontrada.
        """
        for item in deletes:
            delegado_id = item.delegado_id

            asociacion = await sync_to_async(self._core._obtener_asociacion)(
                liquidacion_id=liquidacion_id,
                delegado_id=delegado_id,
            )
            if not asociacion:
                raise HttpError(
                    404,
                    f"El delegado con ID '{delegado_id}' no está asociado a "
                    f"esta liquidación. No se puede eliminar.",
                )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _categoria_esperada_por_tipo(self, tipo_liquidacion: str) -> str:
        """
        Retorna la categoría esperada para un tipo de liquidación.

        Args:
            tipo_liquidacion: Tipo de liquidación (ej. EDIFICACION).

        Returns:
            Categoría esperada o 'desconocida'.
        """
        from modules.liquidaciones.domain.constants import CategoriaDelegado

        categoria_por_tipo = {
            "EDIFICACION": CategoriaDelegado.EDIFICACIONES,
            "HABILITACION_URBANA": CategoriaDelegado.HABILITACIONES_URBANAS,
        }
        return categoria_por_tipo.get(tipo_liquidacion, "desconocida")
