"""
Presenter de Inspección de Obra.
Mapea el Result del Dominio al Schema final de Presentación.

@staticmethod only. Sin acceso a ORM.
"""
import math
import uuid
from typing import List, Optional

from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
)
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasDatosOut,
    LiquidacionInspectorOut,
    LiquidacionContinuidadVisitasOut,
    RegistroPagoInspectorOut,
)
from modules.liquidaciones.presentation.presenters.inspector_presenter import (
    InspectorPresenter,
)
from core.pagination import PaginatedData


class LiquidacionInspeccionObraPresenter:
    @staticmethod
    def _map_inspectores(result) -> list[LiquidacionInspectorOut]:
        """
        Mapea los LiquidacionInspectorResult → LiquidacionInspectorOut.
        Reutiliza InspectorPresenter._map_perfil_ingeniero (sin duplicar el perfil).
        """
        from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
            EspecialidadRevisionOut,
        )

        return [
            LiquidacionInspectorOut(
                id=uuid.UUID(insp.id),
                inspector_id=uuid.UUID(insp.inspector_id) if insp.inspector_id else None,
                inspector_operacion_id=uuid.UUID(insp.inspector_operacion_id) if insp.inspector_operacion_id else None,
                perfil_ingeniero=InspectorPresenter._map_perfil_ingeniero(
                    insp.perfil_ingeniero
                ),
                especialidad_revision=(
                    EspecialidadRevisionOut(
                        id=uuid.UUID(insp.especialidad_revision.id),
                        nombre=insp.especialidad_revision.nombre,
                    )
                    if insp.especialidad_revision
                    else None
                ),
                numero_registro=insp.numero_registro,
                categoria=insp.categoria,
                periodo=insp.periodo,
                mes=insp.mes,
                dictamen_revision=insp.dictamen_revision,
                fecha_presentacion=insp.fecha_presentacion,
                fecha_revision=insp.fecha_revision,
            )
            for insp in (result.inspectores or [])
        ]

    @staticmethod
    def _map_registros_pago(result) -> list[RegistroPagoInspectorOut]:
        """
        Mapea los RegistroPagoResult → RegistroPagoInspectorOut.
        """
        return [
            RegistroPagoInspectorOut(
                id=uuid.UUID(rp.id),
                periodo=rp.periodo,
                mes=rp.mes,
                inspecciones_pagadas=rp.inspecciones_pagadas,
                fecha_registro=rp.fecha_registro,
            )
            for rp in (result.registros_pago or [])
        ]

    @staticmethod
    def _map_continuidad(result) -> Optional[LiquidacionContinuidadVisitasOut]:
        """
        Mapea el LiquidacionContinuidadVisitasResult → LiquidacionContinuidadVisitasOut.

        Devuelve None cuando la IO no tiene continuidad (caso normal: IO sin
        fila de continuidad, comportamiento idéntico al vigente).
        """
        if result is None:
            return None
        return LiquidacionContinuidadVisitasOut(
            id=uuid.UUID(result.id),
            liquidacion_previa_id=(
                uuid.UUID(result.liquidacion_previa_id)
                if result.liquidacion_previa_id
                else None
            ),
            monto_acumulado=float(result.monto_acumulado or 0),
            total_acumulado=float(result.total_acumulado or 0),
            subtotal_credito=float(result.subtotal_credito or 0),
            total_credito=float(result.total_credito or 0),
            visitas_previas_totales=result.visitas_previas_totales,
            visitas_previas_pendientes=result.visitas_previas_pendientes,
            categoria_previa=result.categoria_previa,
            observacion=result.observacion,
        )

    @staticmethod
    def present_primera_revision(
        result: InspeccionObraPrimeraRevisionResult,
    ) -> LiquidacionInspeccionObraOutput:
        """Assembles the final Inspeccion Obra output from the Domain Result."""
        general = result.liquidacion_general
        tipo = result.liquidacion_tipo
        especifica = result.liquidacion_especifica

        general_out = LiquidacionGeneralPresenter.present_liquidacion_general(general)

        tipo_out = LiquidacionTipoOutput(
            id=uuid.UUID(especifica.id),
            numero=especifica.numero,
        )

        especifica_out = LiquidacionPorCategoriaVisitasDatosOut(
            id=uuid.UUID(tipo.id),
            cantidad_visitas=tipo.cantidad_visitas,
            porcentaje_uit=tipo.porcentaje_uit,
            categoria=tipo.categoria,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id) if tipo.tarifa_aplicada_id else None,
            inspectores=LiquidacionInspeccionObraPresenter._map_inspectores(tipo),
            registros_pago=LiquidacionInspeccionObraPresenter._map_registros_pago(tipo),
            continuidad=LiquidacionInspeccionObraPresenter._map_continuidad(
                getattr(tipo, "continuidad", None)
            ),
        )

        return LiquidacionInspeccionObraOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=especifica_out,
        )

    @staticmethod
    def present_list(
        liquidaciones: List[InspeccionObraPrimeraRevisionResult],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedData[LiquidacionInspeccionObraOutput]:
        """
        Maps a list of InspeccionObraPrimeraRevisionResult domain DTOs to PaginatedData[LiquidacionInspeccionObraOutput].

        Each item is presented by calling present_primera_revision.
        Presenter only knows about Domain Results and Schemas — no ORM access.
        """
        items: List[LiquidacionInspeccionObraOutput] = []
        for domain_result in liquidaciones:
            items.append(LiquidacionInspeccionObraPresenter.present_primera_revision(domain_result))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return PaginatedData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def present_detalle(domain_result: InspeccionObraPrimeraRevisionResult) -> LiquidacionInspeccionObraOutput:
        """
        Maps a single InspeccionObraPrimeraRevisionResult domain DTO to LiquidacionInspeccionObraOutput.
        Delegates to present_primera_revision.
        """
        return LiquidacionInspeccionObraPresenter.present_primera_revision(domain_result)
