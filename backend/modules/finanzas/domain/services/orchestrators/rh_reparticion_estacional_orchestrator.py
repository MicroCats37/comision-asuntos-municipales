# -*- coding: utf-8 -*-
"""
RHReparticionEstacionalOrchestrator — thin async facade over Flujo.
"""

import uuid
from typing import Optional

from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.flujos.rh_reparticion_estacional_flujo import (
    RHReparticionEstacionalFlujo,
)
from modules.finanzas.domain.services.core.rh_reparticion_estacional_core_service import (
    RHReparticionEstacionalCoreService,
)
from modules.finanzas.domain.schemas import (
    RHReparticionEstacionalActualizarIn,
    RHReparticionEstacionalCotizarIn,
    RHReparticionEstacionalCrearIn,
)
from modules.finanzas.domain.results.rh_reparticion_estacional_result import (
    RHReparticionEstacionalCotizarResult,
    RHReparticionEstacionalResult,
    RHReparticionEstacionalDelegadoResult,
    RHReparticionEstacionalCapituloResult,
    DelegadoMinimalResult,
    CapituloMinimalResult,
)


class RHReparticionEstacionalOrchestrator:
    """
    Fachada delgada para la repartición estacional.

    Solo delega al flujo — sin lógica de negocio aquí.
    """

    @inject
    def __init__(
        self,
        flujo: RHReparticionEstacionalFlujo,
        core: RHReparticionEstacionalCoreService,
    ):
        self.flujo = flujo
        self.core = core

    def cotizar_proceso(
        self, payload: RHReparticionEstacionalCotizarIn
    ) -> RHReparticionEstacionalCotizarResult:
        """
        Previews the distribution calculation without persisting.

        Args:
            payload: Cotizacion payload with especialidad_revision, periodo, month range, delegates

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown
        """
        esp_rev_pk = self._resolve_especialidad_revision_id(
            payload.especialidad_revision_id
        )
        delegado_pks = self._resolve_delegado_pks(payload.delegado_ids)

        return self.flujo._cotizar(
            especialidad_revision_id=esp_rev_pk,
            periodo=payload.periodo,
            mes_desde=payload.mes_desde,
            mes_hasta=payload.mes_hasta,
            delegado_ids=delegado_pks,
        )

    def crear_proceso(
        self, payload: RHReparticionEstacionalCrearIn
    ) -> RHReparticionEstacionalCotizarResult:
        """
        Validates, calculates and persists the distribution atomically.

        Args:
            payload: Creation payload with especialidad_revision, periodo, month range, delegates

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown and persisted IDs
        """
        esp_rev_pk = self._resolve_especialidad_revision_id(
            payload.especialidad_revision_id
        )
        delegado_pks = self._resolve_delegado_pks(payload.delegado_ids)

        return self.flujo._crear(
            especialidad_revision_id=esp_rev_pk,
            periodo=payload.periodo,
            mes_desde=payload.mes_desde,
            mes_hasta=payload.mes_hasta,
            delegado_ids=delegado_pks,
        )

    def actualizar_proceso(
        self,
        reparticion_id: str,
        payload: RHReparticionEstacionalActualizarIn,
    ) -> RHReparticionEstacionalResult:
        """
        Recalculates and replaces the distribution of a persisted reparticion.

        The record keeps its identity (id) and its creation identity
        (created_at); only the snapshot fields and the FINAL set of details
        are rewritten.

        Args:
            reparticion_id: UUID string of the reparticion to edit.
            payload: Edit payload with especialidad_revision, periodo, month range, delegates

        Returns:
            RHReparticionEstacionalResult — the composed persisted item
            (identidad + general + distribucion), the same shape the list
            endpoint returns.
        """
        try:
            uuid.UUID(reparticion_id)
        except (ValueError, TypeError):
            raise HttpError(400, "reparticion_id no es un UUID válido")

        esp_rev_pk = self._resolve_especialidad_revision_id(
            payload.especialidad_revision_id
        )
        delegado_pks = self._resolve_delegado_pks(payload.delegado_ids)

        reparticion = self.flujo._editar(
            reparticion_id=reparticion_id,
            especialidad_revision_id=esp_rev_pk,
            periodo=payload.periodo,
            mes_desde=payload.mes_desde,
            mes_hasta=payload.mes_hasta,
            delegado_ids=delegado_pks,
        )

        return self._build_result(reparticion)

    @staticmethod
    def _resolve_especialidad_revision_id(especialidad_revision_id: str):
        """
        Resolves an EspecialidadRevision UUID string to its primary key.

        Raises:
            HttpError(400): The value is not a valid UUID.
            HttpError(404): No EspecialidadRevision matches the UUID.
        """
        try:
            esp_rev_uuid = uuid.UUID(especialidad_revision_id)
        except (ValueError, TypeError):
            raise HttpError(400, "especialidad_revision_id no es un UUID válido")

        from modules.usuarios.domain.models.perfil_ingeniero import (
            EspecialidadRevision,
        )

        esp_rev = EspecialidadRevision.objects.filter(id=esp_rev_uuid).first()
        if not esp_rev:
            raise HttpError(404, "EspecialidadRevision no encontrada")

        return esp_rev.id

    @staticmethod
    def _resolve_delegado_pks(delegado_ids: list[str]) -> list:
        """
        Resolves a list of Delegado UUID strings to their primary keys.

        The delegates are the ones manually selected from the active
        candidates of the specialty; the existence of each one is verified
        before the calculation runs.

        Raises:
            HttpError(400): One of the values is not a valid UUID.
            HttpError(404): One of the delegates does not exist.
        """
        from modules.liquidaciones.domain.models.delegado import Delegado

        delegado_pks = []
        for delegado_id_str in delegado_ids:
            try:
                del_uuid = uuid.UUID(delegado_id_str)
            except (ValueError, TypeError):
                raise HttpError(400, "delegado_id no es un UUID válido")
            deleg = Delegado.objects.filter(id=del_uuid).first()
            if not deleg:
                raise HttpError(404, "Delegado no encontrado")
            delegado_pks.append(deleg.id)

        return delegado_pks

    def listar_proceso(
        self,
        especialidad_revision_id: Optional[str] = None,
        periodo: Optional[int] = None,
    ) -> list[RHReparticionEstacionalResult]:
        """
        Lists active (non-deleted) reparticiones.

        Args:
            especialidad_revision_id: Optional UUID string filter
            periodo: Optional year filter

        Returns:
            Complete reparticiones with delegate and chapter distributions.
        """
        esp_rev_pk = None
        if especialidad_revision_id:
            try:
                esp_rev_uuid = uuid.UUID(especialidad_revision_id)
            except (ValueError, TypeError):
                raise HttpError(400, "especialidad_revision_id no es un UUID válido")
            from modules.usuarios.domain.models.perfil_ingeniero import (
                EspecialidadRevision,
            )

            esp_rev = EspecialidadRevision.objects.filter(id=esp_rev_uuid).first()
            if not esp_rev:
                raise HttpError(404, "Especialidad de revisión no encontrada.")
            esp_rev_pk = esp_rev.id

        reparticiones = self.core.get_active_reparticiones(
            especialidad_revision_id=esp_rev_pk,
            periodo=periodo,
        )

        return [self._build_result(reparticion) for reparticion in reparticiones]

    @staticmethod
    def _build_result(reparticion) -> RHReparticionEstacionalResult:
        detalles_delegados = []
        for d in reparticion.detalles_delegados.all():
            perfil = (
                getattr(d.delegado, "perfil_ingeniero", None)
                if hasattr(d, "delegado") and d.delegado
                else None
            )
            detalles_delegados.append(
                RHReparticionEstacionalDelegadoResult(
                    delegado=DelegadoMinimalResult(
                        id=str(d.delegado.id)
                        if hasattr(d.delegado, "id") and d.delegado
                        else "",
                        cip=str(perfil.cip)
                        if perfil and hasattr(perfil, "cip")
                        else "",
                        dni=str(perfil.dni)
                        if perfil and hasattr(perfil, "dni")
                        else "",
                        nombre_completo=str(perfil.nombre_completo)
                        if perfil and hasattr(perfil, "nombre_completo")
                        else "",
                    ),
                    monto=d.monto,
                )
            )

        detalles_capitulos = []
        for d in reparticion.detalles_capitulos.all():
            capitulo_obj = (
                getattr(d, "capitulo", None) if hasattr(d, "capitulo") else None
            )
            detalles_capitulos.append(
                RHReparticionEstacionalCapituloResult(
                    capitulo=CapituloMinimalResult(
                        id=str(capitulo_obj.id)
                        if capitulo_obj and hasattr(capitulo_obj, "id")
                        else "",
                        nombre=str(capitulo_obj.nombre)
                        if capitulo_obj and hasattr(capitulo_obj, "nombre")
                        else "",
                    ),
                    monto=d.monto,
                )
            )

        return RHReparticionEstacionalResult(
            id=str(reparticion.id),
            especialidad_revision_id=str(reparticion.especialidad_revision_id),
            especialidad_revision_nombre=reparticion.especialidad_revision.nombre
            if reparticion.especialidad_revision
            else "",
            periodo=reparticion.periodo,
            mes_desde=reparticion.mes_desde,
            mes_hasta=reparticion.mes_hasta,
            total_fondo_comun=reparticion.total_fondo_comun,
            numero_capitulos=reparticion.numero_capitulos,
            numero_delegados=reparticion.numero_delegados,
            monto_por_participacion=reparticion.monto_por_participacion,
            residual=reparticion.residual,
            created_at=reparticion.created_at.isoformat()
            if reparticion.created_at
            else "",
            detalles_delegados=detalles_delegados,
            detalles_capitulos=detalles_capitulos,
        )

    def eliminar_proceso(self, reparticion_id: str) -> str:
        """
        Soft-deletes a reparticion.

        The row is never physically deleted: ``is_deleted`` is flagged and
        ``deleted_at`` is stamped, so the history remains auditable and a
        new reparticion can replace it.

        Args:
            reparticion_id: UUID string of RHReparticionEstacional

        Returns:
            The UUID string of the soft-deleted reparticion.

        Raises:
            HttpError(400): The identifier is not a valid UUID.
            HttpError(404): The reparticion does not exist.
            HttpError(409): The reparticion was already soft-deleted.
        """
        try:
            uuid.UUID(reparticion_id)
        except (ValueError, TypeError):
            raise HttpError(400, "reparticion_id no es un UUID válido")

        reparticion = self.core.get_reparticion_by_id(reparticion_id)
        if not reparticion:
            raise HttpError(404, "La repartición trimestral no existe.")

        if reparticion.is_deleted:
            raise HttpError(
                409,
                "La repartición trimestral ya fue eliminada.",
            )

        self.core.soft_delete_reparticion(reparticion)
        return str(reparticion.id)
