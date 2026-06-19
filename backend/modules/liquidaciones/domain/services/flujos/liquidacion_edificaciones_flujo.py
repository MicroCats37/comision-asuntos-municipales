"""
Liquidaciones Edificaciones Flujo — flujos async de negocio.

Cada método _proceso_* es un caso de uso completo.
Usa sync_to_async para envolver operaciones ORM del core service.
"""
from __future__ import annotations

import asyncio
import uuid
import datetime
from decimal import Decimal
from typing import Optional, Any, Union

from asgiref.sync import sync_to_async
from injector import inject

from ..core.liquidacion_edificaciones_core_service import LiquidacionesEdificacionesService
from ...schemas import (
    LiquidacionEdificacionesResult,
    NuevaRevisionFormularioResult,
    LiquidacionSnapshotData,
    LiquidacionSnapshotResult,
    RevisionSnapshotData,
    TarifaSnapshotData,
    EntidadSnapshotData,
    ProyectistaSnapshotData,
    ProyectoSnapshotData,
    EdificacionesSnapshotData,
    TotalesSnapshotData,
    MetadataSnapshotData,
    LiquidacionSnapshotFallbackResult,
    ProyectoFallbackData,
    LiquidacionFallbackData,
    EdificacionesFallbackData,
    TotalesFallbackData,
    RevisionCalculoData,
    TarifaCalculoData,
    EspecialidadData,
    RevisionVigenteResult,
    LiquidacionEdificacionesPaginatedResult,
    CotizacionQuoteData,
    CotizacionRevisionData,
    CotizacionTotalesData,
    CotizacionMetadataData,
)
from ...exceptions import (
    ProyectoNotFoundError,
    LiquidacionNotFoundError,
    PrimeraRevisionYaExisteError,
    MaximoRevisionAlcanzadoError,
    RevisionNoHabilitadaError,
    TipoLiquidacionInvalidoError,
)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionEdificaciones,
)
from modules.liquidaciones.domain.constants import TramiteAccion


def _make_json_safe(obj: Any) -> Any:
    """
    Convierte recursivamente objetos no JSON-serializables a sus equivalentes seguros.
    Maneja: UUID, Decimal, date, datetime, sets, bytes.
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(list(obj))
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    return obj


def _to_revision_calculo_data(rev: RevisionVigenteResult):
    """
    Transforma RevisionVigenteResult (flat) en un objeto con la estructura anidada
    esperada por _run_primera_revision (con .tarifa y .especialidad).

    RevisionVigenteResult tiene los campos directamente:
      - derecho_minimo, derecho_maximo, porcentaje_minimo_uit
      - especialidad_nombre (string)

    La estructura anidada esperada tiene:
      - tarifa: TarifaCalculoData con derecho_minimo, derecho_maximo, porcentaje_minimo_uit
      - especialidad: objeto con .nombre
    """
    # Helper que mapea RevisionVigenteResult → estructura con .tarifa y .especialidad
    class _RevisionConTarifa:
        """Objeto fake con .tarifa y .especialidad para compatibilidad."""
        def __init__(self, rev: RevisionVigenteResult):
            self.id = rev.id
            self.especialidad_nombre = rev.especialidad_nombre
            self.porcentaje_liquidacion = rev.porcentaje_liquidacion
            self.habilitada = rev.habilitada
            self.tarifa = TarifaCalculoData(
                id=rev.tarifa_id,
                derecho_minimo=rev.derecho_minimo,
                derecho_maximo=rev.derecho_maximo,
                porcentaje_minimo_uit=rev.porcentaje_minimo_uit,
            )
            self.especialidad = EspecialidadData(
                id=rev.especialidad_id,
                nombre=rev.especialidad_nombre,
            )

    return _RevisionConTarifa(rev)



# Revisiones que cobran: 1, 3, 5, 7
REVISIONES_COBRAN = {1, 3, 5, 7}
MAX_REVISIONES = 7


class LiquidacionesEdificacionesFlujo:
    """
    Flujos async para Liquidaciones Edificaciones.
    """

    @inject
    def __init__(self, core: LiquidacionesEdificacionesService):
        self.core = core

    def _calcular_derecho(
        self,
        monto_base: Decimal,
        derecho_minimo: Decimal,
        derecho_maximo: Optional[Decimal],
    ) -> Decimal:
        """Calcula el derecho aplicando mínimo y máximo."""
        derecho = monto_base
        if derecho < derecho_minimo:
            derecho = derecho_minimo
        if derecho_maximo is not None and derecho > derecho_maximo:
            derecho = derecho_maximo
        return derecho

    def _calcular_monto_base(
        self,
        valor_proyecto: Decimal,
        porcentaje_liquidacion: Decimal,
    ) -> Decimal:
        """Calcula el monto base: valor_proyecto * porcentaje_liquidacion."""
        return Decimal(str(valor_proyecto)) * porcentaje_liquidacion

    async def _proceso_primera_revision(
        self,
        proyecto_public_id: str,
        municipalidad_id: str,
        tipo_tramite: str,
        valor_proyecto: Decimal,
        observacion: Optional[str],
        revisiones_ids: list[str],
        proyectistas_ids: Optional[list[str]] = None,
    ) -> LiquidacionEdificacionesResult:
        """
        Proceso para crear primera revisión (nueva-liquidacion) de edificaciones.

        1. Buscar proyecto por public_id
        2. Buscar municipalidad por ID
        3. Validar que no exista ya revisión 1 para ese proyecto
        4. Obtener IGV/UIT vigentes
        5. Validar revisiones seleccionadas están vigentes/habilitadas
        6. Crear LiquidacionGeneral (con municipalidad y public_id)
        7. Crear LiquidacionEdificaciones (numero_revision=1, tipo_tramite, tramite_accion=PRIMERA_REVISION)
        8. Asociar revisiones
        9. Calcular por cada revisión
        10. Crear snapshot
        11. Retornar resultado
        """
        # 1. Buscar proyecto
        proyecto = await sync_to_async(self.core._obtener_proyecto_por_public_id)(proyecto_public_id)
        if not proyecto:
            raise ProyectoNotFoundError(f"Proyecto con public_id={proyecto_public_id}")

        # 2. Buscar municipalidad
        municipalidad = await self._get_municipalidad_model(municipalidad_id)
        if not municipalidad:
            from ...exceptions import NotFoundError
            raise NotFoundError(f"Municipalidad con id={municipalidad_id}")

        # 3. Validar que no exista primera revisión
        if await sync_to_async(self.core._existe_primera_revision_proyecto)(proyecto.id):
            raise PrimeraRevisionYaExisteError(
                f"Ya existe una primera revisión para el proyecto {proyecto_public_id}"
            )

        # 4. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # 5. Validar revisiones seleccionadas están vigentes/habilitadas
        if revisiones_ids:
            if not await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids):
                raise RevisionNoHabilitadaError(
                    "Una o más revisiones seleccionadas no están habilitadas/vigentes"
                )

        # Obtener datos de revisiones
        if not revisiones_ids:
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_vigentes_result)()
            # Transformar RevisionVigenteResult (flat) a estructura anidada con .tarifa y .especialidad
            revisiones_data = [_to_revision_calculo_data(rev) for rev in revisiones_data]
        else:
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 5-8. Crear liquidación y calcular
        igv_model = await self._get_igv_model(variables.igv_valor)
        uit_model = await self._get_uit_model(variables.uit_valor)

        # Primera revisión siempre cobra
        cobra = True

        # Ejecutar bloque transactional en thread async
        def _run_primera_revision():
            from django.db import transaction

            with transaction.atomic():
                # Crear LiquidacionGeneral (sin numero_revision — va en LiquidacionEdificaciones)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    igv=igv_model,
                    uit=uit_model,
                    valor_proyecto=valor_proyecto,
                    observacion=observacion,
                    liquidacion_previa=None,
                )

                # Crear LiquidacionEdificaciones con numero_revision=1, tipo_tramite y tramite_accion=PRIMERA_REVISION
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    numero_revision=1,
                    tipo_tramite=tipo_tramite,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                    proyectistas_ids=proyectistas_ids,
                )

                # Asociar revisiones
                if revisiones_ids:
                    self.core._asociar_revisiones(liq_edif, revisiones_ids)

                # 8. Calcular por cada revisión usando helper compartido
                revision_results, subtotal, igv_monto, total_liquidacion = self._calcular_revisiones(
                    valor_proyecto=valor_proyecto,
                    revisiones_data=revisiones_data,
                    cobra=cobra,
                    variables=variables,
                    numero_revision=1,  # Primera revisión siempre cobra
                )

                # 9. Crear snapshot
                snapshot_data = self._build_snapshot_data(
                    liquidacion, proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif,
                )
                self.core._crear_snapshot(liquidacion, snapshot_data)

                return liquidacion, liq_edif, revision_results, subtotal, igv_monto, total_liquidacion

        liquidacion, liq_edif, revision_results, subtotal, igv_monto, total_liquidacion = await sync_to_async(_run_primera_revision, thread_sensitive=True)()

        # 10. Retornar resultado (wrap DB access in sync_to_async)
        return await sync_to_async(self._build_result, thread_sensitive=True)(
            liquidacion, proyecto, revision_results,
            subtotal, igv_monto, total_liquidacion, total_liquidacion,
            variables, cobra, liq_edif,
        )

    async def _proceso_nueva_revision(
        self,
        liquidacion_previa_id: str,
        observacion: Optional[str],
        revisiones_ids: list[int],
    ) -> LiquidacionEdificacionesResult:
        """
        Proceso para crear nueva revisión (2da, 3ra, etc.) de edificaciones.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular nuevo numero_revision = previa.edificaciones.numero_revision + 1
        4. Validar <= 7 y que no exista ya esa revisión
        5. Determinar si cobra según número de revisión
        6. Validar revisiones seleccionadas existen y habilitadas
        7. Crear LiquidacionGeneral y LiquidacionEdificaciones (hereda proyectistas de previa)
        8. Si no cobra: cálculos en 0 pero conservar estructura
        9. Si cobra: calcular con porcentajes
        10. Guardar snapshot
        11. Retornar resultado
        """
        # 1. Buscar liquidación previa
        previa = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_previa_id)
        if not previa:
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_previa_id}")

        # 2. Validar que sea de edificaciones
        def _get_liq_edif_previa():
            return LiquidacionEdificaciones.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificaciones.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular nuevo número desde LiquidacionEdificaciones (no LiquidacionGeneral)
        nuevo_numero = liq_edif_previa.numero_revision + 1

        # 4. Validar <= 7 y no exista
        if nuevo_numero > MAX_REVISIONES:
            raise MaximoRevisionAlcanzadoError(
                f"No se puede crear más de {MAX_REVISIONES} revisiones"
            )
        if await sync_to_async(self.core._existe_revision_numero_proyecto)(previa.proyecto_id, nuevo_numero):
            from ...exceptions import ConflictError
            raise ConflictError(
                f"Ya existe la revisión {nuevo_numero} para este proyecto"
            )

        # 5. Determinar si cobra
        cobra = nuevo_numero in REVISIONES_COBRAN

        # 6. Validar revisiones seleccionadas
        if revisiones_ids:
            if not await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids):
                raise RevisionNoHabilitadaError(
                    "Una o más revisiones seleccionadas no están habilitadas/vigentes"
                )

        # Obtener datos de revisiones
        revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids) if revisiones_ids else []

        # Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        igv_model = await self._get_igv_model(variables.igv_valor)
        uit_model = await self._get_uit_model(variables.uit_valor)

        # Obtener valor_proyecto de la liquidación previa
        valor_proyecto = previa.valor_proyecto

        # Obtener ids de proyectistas de la liquidación previa (se heredan)
        proyectistas_ids_previa = list(liq_edif_previa.proyectistas.values_list('id', flat=True))

        # Ejecutar bloque transactional en thread async
        def _run_nueva_revision():
            from django.db import transaction

            with transaction.atomic():
                # 7. Crear LiquidacionGeneral (hereda municipalidad y valor_proyecto de previa)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=previa.proyecto,
                    municipalidad=previa.municipalidad,
                    igv=igv_model,
                    uit=uit_model,
                    valor_proyecto=valor_proyecto,
                    observacion=observacion,
                    liquidacion_previa=previa,
                )

                # Crear LiquidacionEdificaciones con numero_revision, tipo_tramite heredado y tramite_accion=REVISION
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    numero_revision=nuevo_numero,
                    tipo_tramite=liq_edif_previa.tipo_tramite,  # Heredado de la liquidación previa
                    tramite_accion=TramiteAccion.REVISION,
                    proyectistas_ids=proyectistas_ids_previa,
                )

                # Asociar revisiones (siempre se conservan)
                if revisiones_ids:
                    self.core._asociar_revisiones(liq_edif, revisiones_ids)

                # 8-9. Calcular usando helper compartido
                revision_results, subtotal, igv_monto, total_liquidacion = self._calcular_revisiones(
                    valor_proyecto=valor_proyecto,
                    revisiones_data=revisiones_data,
                    cobra=cobra,
                    variables=variables,
                    numero_revision=nuevo_numero,
                )

                # 10. Guardar snapshot
                snapshot_data = self._build_snapshot_data(
                    liquidacion, previa.proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif,
                )
                self.core._crear_snapshot(liquidacion, snapshot_data)

                return liquidacion, liq_edif, revision_results, subtotal, igv_monto, total_liquidacion

        liquidacion, liq_edif, revision_results, subtotal, igv_monto, total_liquidacion = await sync_to_async(_run_nueva_revision, thread_sensitive=True)()

        # 11. Retornar (wrap DB access in sync_to_async)
        return await sync_to_async(self._build_result, thread_sensitive=True)(
            liquidacion, previa.proyecto, revision_results,
            subtotal, igv_monto, total_liquidacion, total_liquidacion,
            variables, cobra, liq_edif,
        )

    async def _proceso_formulario_nueva_revision(
        self,
        liquidacion_previa_id: str,
    ) -> NuevaRevisionFormularioResult:
        """
        Prepara datos para formulario de nueva revisión.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular siguiente número de revisión (desde LiquidacionEdificaciones)
        4. Determinar si cobrará
        5. Obtener revisiones vigentes disponibles
        6. Retornar datos del formulario
        """
        # 1. Buscar liquidación previa
        previa = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_previa_id)
        if not previa:
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_previa_id}")

        # 2. Validar que sea de edificaciones
        def _get_liq_edif_previa():
            return LiquidacionEdificaciones.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificaciones.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular siguiente número desde LiquidacionEdificaciones
        siguiente_numero = liq_edif_previa.numero_revision + 1

        if siguiente_numero > MAX_REVISIONES:
            raise MaximoRevisionAlcanzadoError(
                f"No se puede crear más de {MAX_REVISIONES} revisiones"
            )

        # 4. Determinar si cobrará
        cobra = siguiente_numero in REVISIONES_COBRAN

        # 5. Obtener revisiones vigentes
        revisiones_vigentes = await sync_to_async(self.core._obtener_revisiones_vigentes_result)()

        return NuevaRevisionFormularioResult(
            liquidacion_previa_id=str(liquidacion_previa_id),
            numero_revision=siguiente_numero,
            cobra=cobra,
            proyecto_id=str(previa.proyecto.id),
            proyecto_public_id=previa.proyecto.public_id or "",
            proyecto_nombre=previa.proyecto.denominacion,
            valor_proyecto=previa.valor_proyecto,
            revisiones_vigentes=revisiones_vigentes,
        )

    async def _proceso_obtener_liquidacion(
        self,
        liquidacion_id: str,
    ) -> dict:
        """
        Obtiene el snapshot/detalle de una liquidación.
        Retorna el dict raw de LiquidacionSnapshot.data para preservar
        todos los campos sin proyección.
        """
        # Buscar snapshot
        snapshot = await sync_to_async(self.core._obtener_snapshot_liquidacion)(liquidacion_id)
        if not snapshot:
            # Si no hay snapshot, buscar la liquidación y construir resultado
            liquidacion = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_id)
            if not liquidacion:
                raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_id}")
            # Retornar estructura básica sin snapshot como dict
            return self._build_result_from_liquidacion(liquidacion).model_dump(mode="json")

        # Retornar el dict raw directamente — sin validación Pydantic
        # para preservar todos los campos almacenados (incluyendo _metadata y cualquier campo extra)
        return snapshot.data

    def _build_snapshot_data(
        self,
        liquidacion: LiquidacionGeneral,
        proyecto,
        revision_results: list[RevisionCalculoData],
        subtotal: Decimal,
        igv_monto: Decimal,
        total_liquidacion: Decimal,
        total_a_pagar: Decimal,
        variables,
        cobra: bool,
        liq_edif: LiquidacionEdificaciones,
    ) -> LiquidacionSnapshotResult:
        """Construye el schema tipado del snapshot según la estructura del contexto."""
        # Build nested sections with typed Pydantic models
        entidad_data = None
        if proyecto.entidad:
            entidad_data = EntidadSnapshotData(
                id=str(proyecto.entidad.id),
                tipo=proyecto.entidad.tipo_documento,
                nombre=proyecto.entidad.razon_social,
                ruc=proyecto.entidad.numero_documento,
            )

        # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas
        proyecto_data = ProyectoSnapshotData(
            id=str(proyecto.id),
            public_id=str(proyecto.public_id) if proyecto.public_id else '',
            nombre=proyecto.denominacion,
            direccion=proyecto.direccion or '',
            valor_proyecto=float(liquidacion.valor_proyecto),
            entidad=entidad_data,
        )

        liquidacion_data = LiquidacionSnapshotData(
            id=str(liquidacion.id),
            public_id=liquidacion.public_id or '',
            numero_liquidacion=f"LIQ-EDIF-{liq_edif.numero_revision}",
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            proyecto=proyecto_data,
            municipalidad_id=str(liquidacion.municipalidad.id) if liquidacion.municipalidad else None,
            municipalidad_nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else None,
            # expediente fue removido del modelo
            observacion=liquidacion.observacion or '',
        )

        # Build revisiones from typed RevisionCalculoData
        revisiones_data = []
        for rev in revision_results:
            revisiones_data.append(RevisionSnapshotData(
                id=str(rev.id),
                numero_revision=rev.numero_revision,
                especialidad=rev.especialidad,
                tarifa=TarifaSnapshotData(
                    id=str(rev.tarifa.id),
                    derecho_minimo=str(rev.tarifa.derecho_minimo),
                    derecho_maximo=str(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                    porcentaje_minimo_uit=str(rev.tarifa.porcentaje_minimo_uit),
                ),
                monto_base=float(rev.monto_base),
                cobra=rev.cobra,
                derecho=float(rev.derecho),
            ))

        # Construir proyectistas desde LiquidacionEdificaciones
        proyectistas_data = [
            ProyectistaSnapshotData(
                id=str(p.id),
                cip=p.cip,
                dni=p.dni,
                cap=p.cap,
                nombres=p.nombres,
                apellidos=p.apellidos,
            )
            for p in liq_edif.proyectistas.all()
        ]

        edificaciones_data = EdificacionesSnapshotData(
            public_id=liq_edif.public_id or '',
            numero_revision=liq_edif.numero_revision,
            tipo_tramite=liq_edif.tipo_tramite,
            tramite_accion=liq_edif.tramite_accion,
            proyectistas=proyectistas_data,
            revisiones=revisiones_data,
        )

        totales_data = TotalesSnapshotData(
            subtotal=float(subtotal),
            igv=float(igv_monto),
            total=float(total_liquidacion),
            liquidacion_total=float(total_liquidacion),
            total_a_pagar=float(total_a_pagar),
        )

        metadata_data = MetadataSnapshotData(
            igv_valor=float(variables.igv_valor),
            uit_valor=float(variables.uit_valor),
            cobra=cobra,
        )

        return LiquidacionSnapshotResult(
            liquidacion=liquidacion_data,
            edificaciones=edificaciones_data,
            totales=totales_data,
            _metadata=metadata_data,
        )

    def _build_result(
        self,
        liquidacion: LiquidacionGeneral,
        proyecto,
        revision_results: list[RevisionCalculoData],
        subtotal: Decimal,
        igv_monto: Decimal,
        total_liquidacion: Decimal,
        total_a_pagar: Decimal,
        variables,
        cobra: bool,
        liq_edif: LiquidacionEdificaciones,
    ) -> LiquidacionEdificacionesResult:
        """Construye resultado completo."""
        # Reconstruir revisiones con estructura que coincide con el schema
        from modules.liquidaciones.domain.schemas import EspecialidadData, TarifaEdificacionData, EdificacionRevisionData, ProyectistaSnapshotData

        edificaciones_revisiones = []
        for rev in revision_results:
            edificaciones_revisiones.append(EdificacionRevisionData(
                id=str(rev.id),
                numero_revision=rev.numero_revision,
                especialidad=EspecialidadData(
                    id=str(rev.tarifa.id),  # La especialidad está embebida vía tarifa
                    nombre=rev.especialidad,
                ),
                tarifa=TarifaEdificacionData(
                    id=str(rev.tarifa.id),
                    derecho_minimo=rev.tarifa.derecho_minimo,
                    derecho_maximo=rev.tarifa.derecho_maximo,
                    porcentaje_minimo_uit=rev.tarifa.porcentaje_minimo_uit,
                ),
                porcentaje_liquidacion=Decimal('0'),  # No disponible en este contexto
                habilitada=True,
            ))

        # Construir proyectistas desde LiquidacionEdificaciones
        edificaciones_proyectistas = [
            ProyectistaSnapshotData(
                id=str(p.id),
                cip=p.cip,
                dni=p.dni,
                cap=p.cap,
                nombres=p.nombres,
                apellidos=p.apellidos,
            )
            for p in liq_edif.proyectistas.all()
        ]

        return LiquidacionEdificacionesResult(
            liquidacion_id=str(liquidacion.id),
            liquidacion_public_id=liquidacion.public_id or '',
            numero_revision=liq_edif.numero_revision,  # numero_revision viene de LiquidacionEdificaciones
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            proyecto_id=str(proyecto.id),
            proyecto_public_id=proyecto.public_id or '',
            proyecto_nombre=proyecto.denominacion,
            proyecto_direccion=proyecto.direccion,
            proyecto_entidad_id=str(proyecto.entidad.id) if proyecto.entidad else None,
            proyecto_entidad_tipo=proyecto.entidad.tipo_documento if proyecto.entidad else None,
            proyecto_entidad_nombre=proyecto.entidad.nombre_completo if proyecto.entidad else None,
            proyecto_entidad_ruc=proyecto.entidad.numero_documento if proyecto.entidad else None,
            municipalidad_id=str(liquidacion.municipalidad.id),
            municipalidad_nombre=liquidacion.municipalidad.nombre,
            # NOTE: proyecto_proyectista_* fueron removidos — ahora van en edificaciones_proyectistas
            edificaciones_proyectistas=edificaciones_proyectistas,
            edificaciones_public_id=liq_edif.public_id or '',
            edificaciones_tipo_tramite=liq_edif.tipo_tramite,
            edificaciones_tramite_accion=liq_edif.tramite_accion,
            observacion=liquidacion.observacion,
            edificaciones_revisiones=edificaciones_revisiones,
            igv_valor=variables.igv_valor,
            uit_valor=variables.uit_valor,
            valor_proyecto=liquidacion.valor_proyecto,
            totales_subtotal=subtotal,
            totales_igv=igv_monto,
            totales_total_liquidacion=total_liquidacion,
            totales_total_a_pagar=total_a_pagar,
        )

    def _build_result_from_liquidacion(self, liquidacion: LiquidacionGeneral) -> LiquidacionSnapshotFallbackResult:
        """Construye resultado básico desde liquidación sin snapshot."""
        proyecto = liquidacion.proyecto
        liq_edif = liquidacion.edificaciones if hasattr(liquidacion, 'edificaciones') else None
        numero_revision = liq_edif.numero_revision if liq_edif else 0
        return LiquidacionSnapshotFallbackResult(
            liquidacion=LiquidacionFallbackData(
                id=str(liquidacion.id),
                public_id=liquidacion.public_id or '',
                numero_liquidacion=f"LIQ-EDIF-{numero_revision}",
                estado=liquidacion.estado,
                fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
                proyecto=ProyectoFallbackData(
                    id=str(proyecto.id),
                    public_id=str(proyecto.public_id) if proyecto.public_id else '',
                    nombre=proyecto.denominacion,
                    direccion=proyecto.direccion or '',
                    valor_proyecto=float(liquidacion.valor_proyecto),
                ),
                municipalidad_id=str(liquidacion.municipalidad.id) if liquidacion.municipalidad else None,
                municipalidad_nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else None,
                # expediente fue removido
                observacion=liquidacion.observacion or '',
            ),
            edificaciones=EdificacionesFallbackData(
                public_id=liq_edif.public_id if liq_edif else "",
                numero_revision=numero_revision,
                tipo_tramite=liq_edif.tipo_tramite if liq_edif else "",
                tramite_accion=liq_edif.tramite_accion if liq_edif else "",
                revisiones=[],
            ),
            totales=TotalesFallbackData(
                subtotal=0.0,
                igv=0.0,
                total=0.0,
                liquidacion_total=0.0,
                total_a_pagar=0.0,
            ),
        )

    async def _get_igv_model(self, valor: Decimal):
        """Obtiene modelo IGV por valor."""
        from modules.finanzas.models import IGV
        return await sync_to_async(IGV.objects.filter(valor=valor, periodo_fin__isnull=True).first)()

    async def _get_uit_model(self, valor: Decimal):
        """Obtiene modelo UIT por valor."""
        from modules.finanzas.models import UIT
        return await sync_to_async(UIT.objects.filter(valor=int(valor), periodo_fin__isnull=True).first)()

    async def _get_municipalidad_model(self, municipalidad_id: str):
        """Obtiene modelo Municipalidad por ID."""
        from modules.entidades.models import Municipalidad
        return await sync_to_async(Municipalidad.objects.filter(id=municipalidad_id).first)()

    def _calcular_revisiones(
        self,
        valor_proyecto: Decimal,
        revisiones_data: list,
        cobra: bool,
        variables,
        numero_revision: Optional[int] = None,
    ) -> tuple[list, Decimal, Decimal, Decimal]:
        """
        Calcula el monto base, derecho y totales para una lista de revisiones.

        Args:
            valor_proyecto: Valor del proyecto para el cálculo
            revisiones_data: Lista de revisiones (con .tarifa y .porcentaje_liquidacion)
            cobra: Si True aplica derecho, si False todo es 0
            variables: VariablesFinancierasResult con igv_valor
            numero_revision: Si se proporciona, retorna RevisionCalculoData con este número;
                            si no, retorna CotizacionRevisionData (sin numero_revision por item)

        Returns:
            Tuple of (revision_results, subtotal, igv_monto, total_liquidacion)
        """
        subtotal = Decimal('0')
        revision_results = []

        for rev_data in revisiones_data:
            monto_base = self._calcular_monto_base(
                valor_proyecto,
                rev_data.porcentaje_liquidacion,
            )

            if cobra:
                derecho = self._calcular_derecho(
                    monto_base,
                    rev_data.tarifa.derecho_minimo,
                    rev_data.tarifa.derecho_maximo,
                )
            else:
                derecho = Decimal('0')
                monto_base = Decimal('0')

            if numero_revision is not None:
                # Create flow: RevisionCalculoData con numero_revision por item
                revision_results.append(RevisionCalculoData(
                    id=str(rev_data.id),
                    numero_revision=numero_revision,
                    especialidad=rev_data.especialidad.nombre,
                    tarifa=TarifaCalculoData(
                        id=str(rev_data.tarifa.id),
                        derecho_minimo=rev_data.tarifa.derecho_minimo,
                        derecho_maximo=rev_data.tarifa.derecho_maximo,
                        porcentaje_minimo_uit=rev_data.tarifa.porcentaje_minimo_uit,
                    ),
                    monto_base=monto_base,
                    cobra=cobra,
                    derecho=derecho,
                ))
            else:
                # Cotizar flow: CotizacionRevisionData sin numero_revision por item
                revision_results.append(CotizacionRevisionData(
                    id=rev_data.id,
                    especialidad=rev_data.especialidad.nombre,
                    tarifa=TarifaCalculoData(
                        id=rev_data.tarifa.id,
                        derecho_minimo=rev_data.tarifa.derecho_minimo,
                        derecho_maximo=rev_data.tarifa.derecho_maximo,
                        porcentaje_minimo_uit=rev_data.tarifa.porcentaje_minimo_uit,
                    ),
                    monto_base=monto_base,
                    cobra=cobra,
                    derecho=derecho,
                ))
            subtotal += derecho

        # Calcular totales
        igv_monto = subtotal * variables.igv_valor
        total_liquidacion = subtotal + igv_monto

        return revision_results, subtotal, igv_monto, total_liquidacion

    async def _proceso_cotizar_primera_revision(
        self,
        proyecto_public_id: str,
        valor_proyecto: Decimal,
    ) -> CotizacionQuoteData:
        """
        Cotiza primera revisión sin guardar en BD.

        1. Buscar proyecto por public_id
        2. Obtener IGV/UIT vigentes
        3. Obtener revisiones vigentes (default selection si no se envían)
        4. Calcular con cobra=True (primera siempre cobra)
        5. Retornar resultado de cotización

        No crea ningún registro en BD.
        """
        # 1. Buscar proyecto
        proyecto = await sync_to_async(self.core._obtener_proyecto_por_public_id)(proyecto_public_id)
        if not proyecto:
            raise ProyectoNotFoundError(f"Proyecto con public_id={proyecto_public_id}")

        # 2. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # 3. Obtener revisiones vigentes (default selection — todas las vigentes)
        revisiones_data = await sync_to_async(self.core._obtener_revisiones_vigentes_result)()
        # Transformar RevisionVigenteResult (flat) a estructura anidada con .tarifa y .especialidad
        revisiones_data = [_to_revision_calculo_data(rev) for rev in revisiones_data]

        # 4. Calcular — primera revisión siempre cobra
        cobra = True
        revision_results, subtotal, igv_monto, total_liquidacion = self._calcular_revisiones(
            valor_proyecto=valor_proyecto,
            revisiones_data=revisiones_data,
            cobra=cobra,
            variables=variables,
        )

        # 5. Retornar resultado de cotización
        return CotizacionQuoteData(
            numero_revision=1,
            revisiones=revision_results,
            totales=CotizacionTotalesData(
                subtotal=subtotal,
                igv=igv_monto,
                total=total_liquidacion,
                liquidacion_total=total_liquidacion,
                total_a_pagar=total_liquidacion,
            ),
            metadata=CotizacionMetadataData(
                igv_valor=variables.igv_valor,
                uit_valor=variables.uit_valor,
                cobra=cobra,
            ),
        )

    async def _proceso_cotizar_nueva_revision(
        self,
        liquidacion_previa_id: str,
        revisiones_ids: list[str],
    ) -> CotizacionQuoteData:
        """
        Cotiza nueva revisión sin guardar en BD.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular siguiente número de revisión
        4. Validar <= 7
        5. Obtener IGV/UIT vigentes
        6. Validar y obtener revisiones seleccionadas
        7. Determinar si cobra según número de revisión
        8. Calcular usando valor_proyecto de la liquidación previa
        9. Retornar resultado de cotización

        No crea ningún registro en BD.
        """
        # 1. Buscar liquidación previa
        previa = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_previa_id)
        if not previa:
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_previa_id}")

        # 2. Validar que sea de edificaciones
        def _get_liq_edif_previa():
            return LiquidacionEdificaciones.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificaciones.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular siguiente número
        nuevo_numero = liq_edif_previa.numero_revision + 1

        # 4. Validar <= 7
        if nuevo_numero > MAX_REVISIONES:
            raise MaximoRevisionAlcanzadoError(
                f"No se puede crear más de {MAX_REVISIONES} revisiones"
            )

        # 5. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # 6. Validar y obtener revisiones seleccionadas (siempre requeridas en cotizar)
        if not revisiones_ids:
            raise ValueError("revisiones_ids es requerido para cotizar nueva revisión")

        if not await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids):
            raise RevisionNoHabilitadaError(
                "Una o más revisiones seleccionadas no están habilitadas/vigentes"
            )

        revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 7. Determinar si cobra según número de revisión
        cobra = nuevo_numero in REVISIONES_COBRAN

        # 8. Obtener valor_proyecto de la liquidación previa
        valor_proyecto = previa.valor_proyecto

        # 9. Calcular
        revision_results, subtotal, igv_monto, total_liquidacion = self._calcular_revisiones(
            valor_proyecto=valor_proyecto,
            revisiones_data=revisiones_data,
            cobra=cobra,
            variables=variables,
        )

        # 10. Retornar resultado de cotización
        return CotizacionQuoteData(
            numero_revision=nuevo_numero,
            revisiones=revision_results,
            totales=CotizacionTotalesData(
                subtotal=subtotal,
                igv=igv_monto,
                total=total_liquidacion,
                liquidacion_total=total_liquidacion,
                total_a_pagar=total_liquidacion,
            ),
            metadata=CotizacionMetadataData(
                igv_valor=variables.igv_valor,
                uit_valor=variables.uit_valor,
                cobra=cobra,
            ),
        )

    # === Métodos públicos para orchestrator (delegación) ===

    async def listar_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas — delega a core via sync_to_async."""
        return await sync_to_async(self.core._listar_liquidaciones_paginado_result)(page, page_size)

    async def obtener_revisiones_vigentes(self) -> list[RevisionVigenteResult]:
        """Obtiene todas las revisiones vigentes — delega a core via sync_to_async."""
        return await sync_to_async(self.core._obtener_revisiones_vigentes_result)()

    async def listar_snapshots_paginado(
        self,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """Lista snapshots completos con paginación — delega a core via sync_to_async."""
        return await sync_to_async(self.core._listar_snapshots_paginado)(page, page_size)
