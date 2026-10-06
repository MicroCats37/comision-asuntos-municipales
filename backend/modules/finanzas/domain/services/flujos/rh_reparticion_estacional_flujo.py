# -*- coding: utf-8 -*-
"""
RHReparticionEstacionalFlujo — async flows for cotizar and crear reparticion estacional.

- _cotizar: calculates the distribution without persisting (preview).
- _crear: validates, calculates, and persists the snapshot atomically.

Formula:
    numero_capitulos = count(EspecialidadRevisionCapitulo for especialidad_revision)
    cantidad_delegados = len(selected delegates)
    divisor_total = cantidad_delegados + numero_capitulos
    monto_por_participacion = total_fondo_comun / divisor_total
    each selected delegado receives one share
    each linked capitulo receives one share
"""
from decimal import Decimal

from django.db import transaction
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.core.rh_reparticion_estacional_core_service import (
    RHReparticionEstacionalCoreService,
    distribute_fondo_comun_cents,
)

from modules.finanzas.domain.results.rh_reparticion_estacional_result import (
    RHReparticionEstacionalCotizarResult,
    RHReparticionEstacionalDelegadoResult,
    RHReparticionEstacionalCapituloResult,
    DelegadoMinimalResult,
    CapituloMinimalResult,
)


FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")


class RHReparticionEstacionalFlujo:
    """
    Flujo para la repartición estacional del fondo común.

    Valida y calcula la distribución sin persistir (_cotizar),
    o persiste atómicamente (_crear).
    """

    @inject
    def __init__(self, core: RHReparticionEstacionalCoreService):
        self.core = core

    def _cotizar(
        self,
        especialidad_revision_id: int,
        periodo: int,
        mes_desde: int,
        mes_hasta: int,
        delegado_ids: list[int],
    ) -> RHReparticionEstacionalCotizarResult:
        """
        Calcula la distribución sin persistir (cotización/preview).

        Args:
            especialidad_revision_id: PK of EspecialidadRevision
            periodo: Year (e.g., 2026)
            mes_desde: Starting month (1-12)
            mes_hasta: Ending month (1-12)
            delegado_ids: List of Delegado PKs selected for this distribution

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown

        Raises:
            HttpError(400): No delegates selected, no chapters linked, or invalid month range
        """
        # 1. Get total fondo_comun from DetalleHonorarioDelegado
        total_fondo_comun = self.core.get_fondo_comun_total(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
            mes_desde=mes_desde,
            mes_hasta=mes_hasta,
        )

        if total_fondo_comun <= 0:
            raise HttpError(
                400,
                f"No hay fondo_comun acumulado para la especialidad "
                f"en el periodo {periodo} ({mes_desde}-{mes_hasta}).",
            )

        # 2. Get chapters linked to this especialidad_revision
        capitulo_ids = self.core.get_capitulos_for_especialidad(especialidad_revision_id)
        numero_capitulos = len(capitulo_ids)

        # 3. Delegate count
        cantidad_delegados = len(delegado_ids)

        if cantidad_delegados == 0:
            raise HttpError(400, "Debe seleccionar al menos un delegado")

        if numero_capitulos == 0:
            raise HttpError(
                400,
                "No hay capítulos vinculados a la especialidad.",
            )

        # 4. Calculate exact-cent distribution
        # Chapters get all leftover cents (distributed evenly); delegates get base only.
        divisor_total = cantidad_delegados + numero_capitulos
        capitulo_amounts, delegado_amounts, monto_por_participacion, residual = distribute_fondo_comun_cents(
            total=total_fondo_comun,
            capitulo_ids=capitulo_ids,
            delegado_ids=delegado_ids,
        )

        # 5. Batch-fetch delegate profile data (avoid N+1)
        from modules.liquidaciones.domain.models.delegado import Delegado
        from modules.usuarios.domain.models.perfil_ingeniero import Capitulo

        # Fetch all selected delegates with their perfil_ingeniero in one query
        delegados_map: dict[int, Delegado] = {}
        if delegado_ids:
            delegados_qs = Delegado.objects.select_related("perfil_ingeniero").filter(
                id__in=delegado_ids
            )
            delegados_map = {d.id: d for d in delegados_qs}

        # Fetch all chapters by IDs in one query
        capitulos_map: dict[int, Capitulo] = {}
        if capitulo_ids:
            capitulos_qs = Capitulo.objects.filter(id__in=capitulo_ids)
            capitulos_map = {c.id: c for c in capitulos_qs}

        # 6. Build detail records with nested objects using computed per-recipient amounts
        # Use sorted lists for deterministic order matching the helper's internal ordering
        detalles_delegados = [
            RHReparticionEstacionalDelegadoResult(
                delegado_id=str(delegado_id),
                delegado=DelegadoMinimalResult(
                    id=str(delegados_map[delegado_id].id),
                    cip=delegados_map[delegado_id].perfil_ingeniero.cip,
                    dni=delegados_map[delegado_id].perfil_ingeniero.dni,
                    nombre_completo=delegados_map[delegado_id].perfil_ingeniero.nombre_completo,
                )
                if delegado_id in delegados_map
                else DelegadoMinimalResult(id=str(delegado_id), cip="", dni="", nombre_completo=""),
                monto=delegado_amounts.get(delegado_id, monto_por_participacion),
            )
            for delegado_id in sorted(delegado_ids)
        ]

        detalles_capitulos = [
            RHReparticionEstacionalCapituloResult(
                capitulo_id=str(capitulo_id),
                capitulo=CapituloMinimalResult(
                    id=str(capitulos_map[capitulo_id].id),
                    nombre=capitulos_map[capitulo_id].nombre,
                )
                if capitulo_id in capitulos_map
                else CapituloMinimalResult(id=str(capitulo_id), nombre=""),
                monto=capitulo_amounts.get(capitulo_id, monto_por_participacion),
            )
            for capitulo_id in sorted(capitulo_ids)
        ]

        # 7. residual is always 0.00 — total is exactly distributed

        # 8. Get especialidad_revision nombre for response
        from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
        esp_rev = EspecialidadRevision.objects.filter(id=especialidad_revision_id).first()
        esp_rev_nombre = esp_rev.nombre if esp_rev else str(especialidad_revision_id)

        return RHReparticionEstacionalCotizarResult(
            especialidad_revision_id=str(especialidad_revision_id),
            especialidad_revision_nombre=esp_rev_nombre,
            periodo=periodo,
            mes_desde=mes_desde,
            mes_hasta=mes_hasta,
            total_fondo_comun=total_fondo_comun,
            numero_capitulos=numero_capitulos,
            numero_delegados=cantidad_delegados,
            divisor_total=divisor_total,
            monto_por_participacion=monto_por_participacion,
            residual=residual,
            detalles_delegados=detalles_delegados,
            detalles_capitulos=detalles_capitulos,
        )

    def _crear(
        self,
        especialidad_revision_id: int,
        periodo: int,
        mes_desde: int,
        mes_hasta: int,
        delegado_ids: list[int],
    ) -> RHReparticionEstacionalCotizarResult:
        """
        Valida, calcula y persiste la distribución atómicamente.

        Args:
            especialidad_revision_id: PK of EspecialidadRevision
            periodo: Year (e.g., 2026)
            mes_desde: Starting month (1-12)
            mes_hasta: Ending month (1-12)
            delegado_ids: List of Delegado PKs selected for this distribution

        Returns:
            RHReparticionEstacionalCotizarResult with full breakdown and IDs

        Raises:
            HttpError(400): Overlapping month range detected
            HttpError(400): Validation errors from _cotizar
        """
        # 1. Validate month range
        if mes_desde > mes_hasta:
            raise HttpError(400, "mes_desde no puede ser mayor que mes_hasta")

        # 2. Check for overlapping distributions
        has_overlap = self.core.check_overlapping_reparticion(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
            mes_desde=mes_desde,
            mes_hasta=mes_hasta,
        )
        if has_overlap:
            raise HttpError(
                400,
                f"Ya existe una repartición activa para la especialidad "
                f"en el periodo {periodo} con rango de meses que se superpone a {mes_desde}-{mes_hasta}.",
            )

        # 3. Calculate (reuse cotizar logic)
        result = self._cotizar(
            especialidad_revision_id=especialidad_revision_id,
            periodo=periodo,
            mes_desde=mes_desde,
            mes_hasta=mes_hasta,
            delegado_ids=delegado_ids,
        )

        # 4. Persist atomically
        with transaction.atomic():
            # Create main snapshot
            reparticion = self.core.create_reparticion(
                especialidad_revision_id=especialidad_revision_id,
                periodo=periodo,
                total_fondo_comun=result.total_fondo_comun,
                numero_capitulos=result.numero_capitulos,
                numero_delegados=result.numero_delegados,
                monto_por_participacion=result.monto_por_participacion,
                residual=result.residual,
                mes_desde=mes_desde,
                mes_hasta=mes_hasta,
            )

            # Create delegate details
            for detalle in result.detalles_delegados:
                self.core.create_detalle_delegado(
                    reparticion=reparticion,
                    delegado_id=str(detalle.delegado_id),
                    monto=detalle.monto,
                )

            # Create chapter details
            for detalle in result.detalles_capitulos:
                self.core.create_detalle_capitulo(
                    reparticion=reparticion,
                    capitulo_id=str(detalle.capitulo_id),
                    monto=detalle.monto,
                )

        return result
