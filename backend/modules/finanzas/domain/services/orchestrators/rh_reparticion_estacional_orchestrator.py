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
from modules.finanzas.domain.schemas import RHReparticionEstacionalCotizarIn, RHReparticionEstacionalCrearIn
from modules.finanzas.domain.results.rh_reparticion_estacional_result import (
    RHReparticionEstacionalCotizarResult,
    RHReparticionEstacionalListItemResult,
    RHReparticionEstacionalDetalleResult,
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

    def cotizar_proceso(self, payload: RHReparticionEstacionalCotizarIn) -> RHReparticionEstacionalCotizarResult:
        """
        Previews the distribution calculation without persisting.

        Args:
            payload: Cotizacion payload with especialidad_revision, periodo, month range, delegates

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown
        """
        try:
            esp_rev_uuid = uuid.UUID(payload.especialidad_revision_id)
        except (ValueError, TypeError):
            raise HttpError(400, "especialidad_revision_id no es un UUID válido")

        # Convert string UUIDs to ints if needed (core service expects int PKs)
        # Actually the core service uses int PKs, but UUIDs are stored as UUID
        # Let's resolve the PK by looking up the record
        from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
        esp_rev = EspecialidadRevision.objects.filter(id=esp_rev_uuid).first()
        if not esp_rev:
            raise HttpError(404, "EspecialidadRevision no encontrada")

        # Resolve delegado UUIDs to PKs
        from modules.liquidaciones.domain.models.delegado import Delegado
        delegado_pks = []
        for delegado_id_str in payload.delegado_ids:
            try:
                del_uuid = uuid.UUID(delegado_id_str)
            except (ValueError, TypeError):
                raise HttpError(400, "delegado_id no es un UUID válido")
            deleg = Delegado.objects.filter(id=del_uuid).first()
            if not deleg:
                raise HttpError(404, "Delegado no encontrado")
            delegado_pks.append(deleg.id)

        return self.flujo._cotizar(
            especialidad_revision_id=esp_rev.id,
            periodo=payload.periodo,
            mes_desde=payload.mes_desde,
            mes_hasta=payload.mes_hasta,
            delegado_ids=delegado_pks,
        )

    def crear_proceso(self, payload: RHReparticionEstacionalCrearIn) -> RHReparticionEstacionalCotizarResult:
        """
        Validates, calculates and persists the distribution atomically.

        Args:
            payload: Creation payload with especialidad_revision, periodo, month range, delegates

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown and persisted IDs
        """
        try:
            esp_rev_uuid = uuid.UUID(payload.especialidad_revision_id)
        except (ValueError, TypeError):
            raise HttpError(400, "especialidad_revision_id no es un UUID válido")

        from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
        esp_rev = EspecialidadRevision.objects.filter(id=esp_rev_uuid).first()
        if not esp_rev:
            raise HttpError(404, "EspecialidadRevision no encontrada")

        # Resolve delegado UUIDs to PKs
        from modules.liquidaciones.domain.models.delegado import Delegado
        delegado_pks = []
        for delegado_id_str in payload.delegado_ids:
            try:
                del_uuid = uuid.UUID(delegado_id_str)
            except (ValueError, TypeError):
                raise HttpError(400, "delegado_id no es un UUID válido")
            deleg = Delegado.objects.filter(id=del_uuid).first()
            if not deleg:
                raise HttpError(404, "Delegado no encontrado")
            delegado_pks.append(deleg.id)

        return self.flujo._crear(
            especialidad_revision_id=esp_rev.id,
            periodo=payload.periodo,
            mes_desde=payload.mes_desde,
            mes_hasta=payload.mes_hasta,
            delegado_ids=delegado_pks,
        )

    def listar_proceso(
        self,
        especialidad_revision_id: Optional[str] = None,
        periodo: Optional[int] = None,
    ) -> list[RHReparticionEstacionalListItemResult]:
        """
        Lists active (non-deleted) reparticiones.

        Args:
            especialidad_revision_id: Optional UUID string filter
            periodo: Optional year filter

        Returns:
            List of RHReparticionEstacionalListItemResult
        """
        esp_rev_pk = None
        if especialidad_revision_id:
            try:
                esp_rev_uuid = uuid.UUID(especialidad_revision_id)
            except (ValueError, TypeError):
                raise HttpError(400, "especialidad_revision_id no es un UUID válido")
            from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
            esp_rev = EspecialidadRevision.objects.filter(id=esp_rev_uuid).first()
            if not esp_rev:
                raise HttpError(404, f"EspecialidadRevision '{esp_rev.nombre}' no encontrada")
            esp_rev_pk = esp_rev.id

        reparticiones = self.core.get_active_reparticiones(
            especialidad_revision_id=esp_rev_pk,
            periodo=periodo,
        )

        results = []
        for rep in reparticiones:
            results.append(
                RHReparticionEstacionalListItemResult(
                    id=str(rep.id),
                    especialidad_revision_id=str(rep.especialidad_revision_id),
                    especialidad_revision_nombre=rep.especialidad_revision.nombre if rep.especialidad_revision else "",
                    periodo=rep.periodo,
                    total_fondo_comun=rep.total_fondo_comun,
                    numero_delegados=rep.numero_delegados,
                    numero_capitulos=rep.numero_capitulos,
                    monto_por_participacion=rep.monto_por_participacion,
                    residual=rep.residual,
                    is_deleted=rep.is_deleted,
                    created_at=rep.created_at.isoformat() if rep.created_at else "",
                )
            )
        return results

    def obtener_detalle_proceso(self, reparticion_id: str) -> RHReparticionEstacionalDetalleResult:
        """
        Gets full detail of a single reparticion including delegate and chapter details.

        Args:
            reparticion_id: UUID string of RHReparticionEstacional

        Returns:
            RHReparticionEstacionalDetalleResult
        """
        try:
            uuid.UUID(reparticion_id)
        except (ValueError, TypeError):
            raise HttpError(400, "reparticion_id no es un UUID válido")

        reparticion = self.core.get_reparticion_by_id(reparticion_id)
        if not reparticion:
            raise HttpError(404, "RHReparticionEstacional no encontrada")

        detalles_delegados = []
        for d in reparticion.detalles_delegados.all():
            perfil = getattr(d.delegado, "perfil_ingeniero", None) if hasattr(d, "delegado") and d.delegado else None
            detalles_delegados.append(
                RHReparticionEstacionalDelegadoResult(
                    delegado_id=str(d.delegado_id),
                    delegado=DelegadoMinimalResult(
                        id=str(d.delegado.id) if hasattr(d.delegado, "id") and d.delegado else "",
                        cip=str(perfil.cip) if perfil and hasattr(perfil, "cip") else "",
                        dni=str(perfil.dni) if perfil and hasattr(perfil, "dni") else "",
                        nombre_completo=str(perfil.nombre_completo) if perfil and hasattr(perfil, "nombre_completo") else "",
                    ),
                    monto=d.monto,
                )
            )

        detalles_capitulos = []
        for d in reparticion.detalles_capitulos.all():
            capitulo_obj = getattr(d, "capitulo", None) if hasattr(d, "capitulo") else None
            detalles_capitulos.append(
                RHReparticionEstacionalCapituloResult(
                    capitulo_id=str(d.capitulo_id),
                    capitulo=CapituloMinimalResult(
                        id=str(capitulo_obj.id) if capitulo_obj and hasattr(capitulo_obj, "id") else "",
                        nombre=str(capitulo_obj.nombre) if capitulo_obj and hasattr(capitulo_obj, "nombre") else "",
                    ),
                    monto=d.monto,
                )
            )

        return RHReparticionEstacionalDetalleResult(
            id=str(reparticion.id),
            especialidad_revision_id=str(reparticion.especialidad_revision_id),
            especialidad_revision_nombre=reparticion.especialidad_revision.nombre if reparticion.especialidad_revision else "",
            periodo=reparticion.periodo,
            mes_desde=reparticion.mes_desde,
            mes_hasta=reparticion.mes_hasta,
            total_fondo_comun=reparticion.total_fondo_comun,
            numero_capitulos=reparticion.numero_capitulos,
            numero_delegados=reparticion.numero_delegados,
            monto_por_participacion=reparticion.monto_por_participacion,
            residual=reparticion.residual,
            is_deleted=reparticion.is_deleted,
            created_at=reparticion.created_at.isoformat() if reparticion.created_at else "",
            detalles_delegados=detalles_delegados,
            detalles_capitulos=detalles_capitulos,
        )

    def eliminar_proceso(self, reparticion_id: str) -> dict:
        """
        Soft-deletes a reparticion.

        Args:
            reparticion_id: UUID string of RHReparticionEstacional

        Returns:
            dict with success message
        """
        try:
            uuid.UUID(reparticion_id)
        except (ValueError, TypeError):
            raise HttpError(400, "reparticion_id no es un UUID válido")

        reparticion = self.core.get_reparticion_by_id(reparticion_id)
        if not reparticion:
            raise HttpError(404, "RHReparticionEstacional no encontrada")

        self.core.soft_delete_reparticion(reparticion)
        return {"message": f"ReparticionEstacional eliminada correctamente"}
