"""
Liquidaciones Edificaciones Flujo — flujos async de negocio.

Cada método _proceso_* es un caso de uso completo.
Usa sync_to_async para envolver operaciones ORM del core service.

La construcción de DTOs de resultado (snapshots, results, fallback) está
delegada a LiquidacionEdificacionesResultBuilder en domain/services/builders/,
separando así la responsabilidad de coordinación de pasos de negocio (el flujo)
de la responsabilidad de construcción de estructuras de datos (el builder).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from asgiref.sync import sync_to_async
from injector import inject

from ..core.liquidacion_edificaciones_core_service import LiquidacionesEdificacionesService
from ..builders import LiquidacionEdificacionesResultBuilder
from ...schemas import (
    NuevaRevisionFormularioResult,
    RevisionVigenteResult,
    LiquidacionEdificacionesPaginatedResult,
    CotizacionQuoteData,
    CotizacionTotalesData,
    CotizacionMetadataData,
    ProyectistaInlineData,
    ContactoInlineData,
    DelegadoVigenteResult,
    DelegadosVigentesResult,
)
from ...exceptions import (
    ProyectoNotFoundError,
    LiquidacionNotFoundError,
    PrimeraRevisionYaExisteError,
    MaximoRevisionAlcanzadoError,
    RevisionNoHabilitadaError,
    TipoLiquidacionInvalidoError,
    EspecialidadesGrupoNoEncontradoError,
    EspecialidadesSetInvalidoError,
    RevisionesMultipleError,
)
from modules.liquidaciones.models import LiquidacionEdificaciones
from modules.liquidaciones.domain.constants import TramiteAccion
from modules.usuarios.infrastructure.services import ICipClient
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService


# Revisiones que cobran: 1, 3, 5, 7
REVISIONES_COBRAN = {1, 3, 5, 7}
MAX_REVISIONES = 7


class LiquidacionesEdificacionesFlujo:
    """
    Flujos async para Liquidaciones Edificaciones.
    """

    @inject
    def __init__(
        self,
        core: LiquidacionesEdificacionesService,
        cip_client: ICipClient,
        perfil_ingeniero_core: PerfilIngenieroCoreService,
    ):
        self.core = core
        self._cip_client = cip_client
        self._perfil_ingeniero_core = perfil_ingeniero_core

    async def _proceso_primera_revision(
        self,
        proyecto_public_id: str,
        municipalidad_id: str,
        tipo_tramite: str,
        valor_proyecto: Decimal,
        expediente: Optional[str],
        valor_base_calculo: Optional[Decimal],
        observacion: Optional[str],
        revisiones_ids: list[str],
        proyectistas_inline: Optional[list[ProyectistaInlineData]] = None,
        proyectistas_ids: Optional[list[str]] = None,
        delegados_ids: Optional[list[str]] = None,
        contactos_inline: Optional[list[ContactoInlineData]] = None,
    ):
        """
        Proceso para crear primera revisión (nueva-liquidacion) de edificaciones.

        1. Buscar proyecto por public_id
        2. Buscar municipalidad por ID
        3. Validar que no exista ya revisión 1 para ese proyecto
        4. Obtener IGV/UIT vigentes
        5. Validar revisiones seleccionadas están vigentes/habilitadas
        6. Si hay proyectistas_inline (inline con CIP):
           - Validar TODOS los CIPs via servicio externo (ALL-OR-NOTHING)
           - Si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        7. Validar delegados (si se proveen)
        8. Crear LiquidacionGeneral (con municipalidad y public_id)
        9. Crear LiquidacionEdificaciones con proyectistas upsertados
        10. Asociar revisiones y delegados
        11. Calcular por cada revisión
        12. Crear snapshot
        13. Retornar resultado
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
            revisiones_data = [self.core.to_revision_con_tarifa(rev) for rev in revisiones_data]
        else:
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 5b. Validar exact-set de especialidades vigentes (primera revisión)
        await self._validar_especialidades_exact_set(revisiones_data)

        # 6. Si hay proyectistas_inline (inline con CIP), validar TODOS los CIPs
        # ALL-OR-NOTHING: si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        if proyectistas_inline:
            await self._validar_proyectistas_inline_cip(proyectistas_inline)

        # 7. Validar delegados si se proveen
        if delegados_ids:
            await self._validar_delegados_ids(delegados_ids, municipalidad_id)

        # 5-8. Crear liquidación y calcular
        # Primera revisión siempre cobra
        cobra = True

        # Validar valor_base_calculo según tipo_tramite
        from ..validators import validate_valor_base_calculo
        validate_valor_base_calculo(
            valor_proyecto=valor_proyecto,
            valor_base_calculo=valor_base_calculo if valor_base_calculo is not None else valor_proyecto,
            tipo_tramite=tipo_tramite,
        )

        # Ejecutar bloque transactional en thread async
        def _run_primera_revision():
            from django.db import transaction

            with transaction.atomic():
                # Crear LiquidacionGeneral (sin numero_revision — va en LiquidacionEdificaciones)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    valor_proyecto=valor_proyecto,
                    expediente=expediente,
                    valor_base_calculo=valor_base_calculo,
                    observacion=observacion,
                    liquidacion_previa=None,
                )

                # 8. Crear/upsertear proyectistas desde inline data si existe
                final_proyectistas_ids = None
                if proyectistas_inline:
                    final_proyectistas_ids = self._upsert_proyectistas_inline(
                        proyectistas_inline, municipalidad_id
                    )
                # Si no hay inline data pero sí proyectistas_ids (backwards compat), usar esos
                elif proyectistas_ids:
                    final_proyectistas_ids = proyectistas_ids

                # Crear LiquidacionEdificaciones con numero_revision=1, tipo_tramite y tramite_accion=PRIMERA_REVISION
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    numero_revision=1,
                    tipo_tramite=tipo_tramite,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                    proyectistas_ids=final_proyectistas_ids,
                )

                # Asociar revisiones
                if revisiones_ids:
                    self.core._asociar_revisiones(liq_edif, revisiones_ids)

                # Asociar delegados si se proveen
                if delegados_ids:
                    self._asociar_delegados(liq_edif, delegados_ids)

                if contactos_inline:
                    self._crear_contactos_inline(liquidacion, contactos_inline)

                # 8. Calcular por cada revisión usando helper compartido del core service
                # Usar valor_base_calculo (ya validado que es igual a valor_proyecto para tipos normales)
                revision_results, subtotal, igv_monto, total_liquidacion = self.core.calcular_revisiones(
                    valor_base_calculo=valor_base_calculo if valor_base_calculo is not None else valor_proyecto,
                    revisiones_data=revisiones_data,
                    cobra=cobra,
                    igv_valor=variables.igv_valor,
                    numero_revision=1,  # Primera revisión siempre cobra
                )

                # 8b. Guardar sub_total y valor_base_calculo en LiquidacionGeneral
                liquidacion.sub_total = subtotal
                liquidacion.save(update_fields=['sub_total'])

                # 9. Crear snapshot — delega al builder (dentro del contexto sync)
                snapshot_data = LiquidacionEdificacionesResultBuilder.build_snapshot_data(
                    liquidacion, proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif,
                )
                self.core._crear_snapshot(liquidacion, snapshot_data)

                # 10. Construir resultado — delega al builder (dentro del contexto sync)
                # Pre-materializar proyectistas antes de retornar para evitar acceso ORM en contexto async
                edificaciones_proyectistas = list(
                    liq_edif.proyectistas.select_related('perfil_ingeniero', 'especialidad').all()
                )
                edificaciones_delegados = list(
                    liq_edif.liquidacion.liquidacion_delegados.select_related(
                        'delegado__perfil_ingeniero', 'delegado__especialidad'
                    ).all()
                )
                result = LiquidacionEdificacionesResultBuilder.build_result(
                    liquidacion, proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif, edificaciones_proyectistas, edificaciones_delegados,
                )
                return result

        return await sync_to_async(_run_primera_revision, thread_sensitive=True)()

    async def _proceso_nueva_revision(
        self,
        liquidacion_previa_id: str,
        observacion: Optional[str],
        revisiones_ids: list[int],
        proyectistas_inline: Optional[list[ProyectistaInlineData]] = None,
        proyectistas_ids: Optional[list[str]] = None,
        delegados_ids: Optional[list[str]] = None,
        contactos_inline: Optional[list[ContactoInlineData]] = None,
    ):
        """
        Proceso para crear nueva revisión (2da, 3ra, etc.) de edificaciones.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular nuevo numero_revision = previa.edificaciones.numero_revision + 1
        4. Validar <= 7 y que no exista ya esa revisión
        5. Determinar si cobra según número de revisión
        6. Validar revisiones seleccionadas existen y habilitadas
        7. Si hay proyectistas_inline (inline con CIP):
           - Validar TODOS los CIPs via servicio externo (ALL-OR-NOTHING)
           - Si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        8. Determinar proyectistas:
           - Si se proporcionó y no está vacío, usar esos (inline o IDs)
           - Si se omitió o está vacío, heredar de la liquidación previa
        9. Validar delegados (si se proveen, o heredar si se omiten)
        10. Crear LiquidacionGeneral y LiquidacionEdificaciones
        11. Si no cobra: cálculos en 0 pero conservar estructura
        12. Si cobra: calcular con porcentajes
        13. Guardar snapshot
        14. Retornar resultado
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

        # 6. Validar revisiones seleccionadas - exactamente UNA para nueva revisión
        if revisiones_ids:
            if len(revisiones_ids) != 1:
                from ...exceptions import RevisionesMultipleError
                raise RevisionesMultipleError(
                    f"Se requiere exactamente UNA revisión para nueva revisión, pero se enviaron {len(revisiones_ids)}."
                )
            if not await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids):
                raise RevisionNoHabilitadaError(
                    "Una o más revisiones seleccionadas no están habilitadas/vigentes"
                )

        # Obtener datos de revisiones
        revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids) if revisiones_ids else []

        # Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # Obtener valor_proyecto y valor_base_calculo de la liquidación previa
        # valor_base_calculo se hereda de la liquidación previa para mantener consistencia
        valor_proyecto = previa.valor_proyecto
        valor_base_calculo = previa.valor_base_calculo if previa.valor_base_calculo is not None else valor_proyecto

        # 7. Determinar proyectistas y delegados:
        # - Si se proporcionó proyectistas_inline (inline con CIP), validar CIPs primero
        # - Si se proporcionó proyectistas_ids, usar esos
        # - Si se omitió ambos, heredar de la liquidación previa
        if proyectistas_inline:
            # Validar inline CIPs antes de la transacción
            await self._validar_proyectistas_inline_cip(proyectistas_inline)
            final_proyectistas_ids = None  # Se manejarán dentro de la transacción
            final_delegados_ids = None  # Se manejarán dentro de la transacción
        elif proyectistas_ids and len(proyectistas_ids) > 0:
            # Usar los IDs proporcionados
            final_proyectistas_ids = [str(pid) for pid in proyectistas_ids]
            final_delegados_ids = None  # Se manejarán dentro de la transacción
        else:
            # Heredar de la liquidación previa
            final_proyectistas_ids = list(liq_edif_previa.proyectistas.values_list('id', flat=True))
            final_delegados_ids = None  # Se heredarán dentro de la transacción si no se especifican

        # 8. Validar/modificar delegados si se proveen
        if delegados_ids:
            await self._validar_delegados_ids(delegados_ids, str(previa.municipalidad_id))
        elif final_delegados_ids is None:
            # Heredar delegados de la liquidación previa si no se especificaron
            final_delegados_ids = list(
                liq_edif_previa.liquidacion.liquidacion_delegados.values_list('delegado_id', flat=True)
            )

        # Ejecutar bloque transactional en thread async
        def _run_nueva_revision():
            from django.db import transaction

            with transaction.atomic():
                # 8. Crear/upsertear proyectistas desde inline data si existe
                if proyectistas_inline:
                    final_proyectistas_ids = self._upsert_proyectistas_inline(
                        proyectistas_inline, str(previa.municipalidad_id)
                    )

                # 9. Crear LiquidacionGeneral (hereda municipalidad y valor_proyecto de previa)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=previa.proyecto,
                    municipalidad=previa.municipalidad,
                    valor_proyecto=valor_proyecto,
                    observacion=observacion,
                    liquidacion_previa=previa,
                )

                # 10. Crear LiquidacionEdificaciones con numero_revision, tipo_tramite heredado y tramite_accion=REVISION
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    numero_revision=nuevo_numero,
                    tipo_tramite=liq_edif_previa.tipo_tramite,  # Heredado de la liquidación previa
                    tramite_accion=TramiteAccion.REVISION,
                    proyectistas_ids=final_proyectistas_ids,
                )

                # Asociar revisiones (siempre se conservan)
                if revisiones_ids:
                    self.core._asociar_revisiones(liq_edif, revisiones_ids)

                # Asociar delegados
                if delegados_ids:
                    self._asociar_delegados(liq_edif, delegados_ids)
                elif final_delegados_ids and len(final_delegados_ids) > 0:
                    # Heredar delegados de la liquidación previa
                    self._asociar_delegados(liq_edif, final_delegados_ids)

                if contactos_inline:
                    self._crear_contactos_inline(liquidacion, contactos_inline)

                # 9-10. Calcular usando helper compartido del core service
                # Usar valor_base_calculo heredado de la liquidación previa
                revision_results, subtotal, igv_monto, total_liquidacion = self.core.calcular_revisiones(
                    valor_base_calculo=valor_base_calculo,
                    revisiones_data=revisiones_data,
                    cobra=cobra,
                    igv_valor=variables.igv_valor,
                    numero_revision=nuevo_numero,
                )

                # 10b. Guardar sub_total y valor_base_calculo en LiquidacionGeneral
                liquidacion.sub_total = subtotal
                liquidacion.save(update_fields=['sub_total'])

                # 11. Guardar snapshot — delega al builder (dentro del contexto sync)
                snapshot_data = LiquidacionEdificacionesResultBuilder.build_snapshot_data(
                    liquidacion, previa.proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif,
                )
                self.core._crear_snapshot(liquidacion, snapshot_data)

                # 12. Construir resultado — delega al builder (dentro del contexto sync)
                # Pre-materializar proyectistas antes de retornar para evitar acceso ORM en contexto async
                edificaciones_proyectistas = list(
                    liq_edif.proyectistas.select_related('perfil_ingeniero', 'especialidad').all()
                )
                edificaciones_delegados = list(
                    liq_edif.liquidacion.liquidacion_delegados.select_related(
                        'delegado__perfil_ingeniero', 'delegado__especialidad'
                    ).all()
                )
                result = LiquidacionEdificacionesResultBuilder.build_result(
                    liquidacion, previa.proyecto, revision_results,
                    subtotal, igv_monto, total_liquidacion, total_liquidacion,
                    variables, cobra, liq_edif, edificaciones_proyectistas, edificaciones_delegados,
                )
                return result

        return await sync_to_async(_run_nueva_revision, thread_sensitive=True)()

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
        6. Obtener proyectistas actuales (heredados de la liquidación previa)
        7. Retornar datos del formulario
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

        # 6. Obtener proyectistas actuales (heredados de la liquidación previa)
        # Delegar construcción de ProyectistaSnapshotData al builder para
        # mantener el flujo enfocado en coordinación de pasos de negocio.
        # El builder recibe instancias ORM y produce domain DTOs (ProyectistaSnapshotData).
        def _get_proyectistas():
            return list(liq_edif_previa.proyectistas.select_related('perfil_ingeniero', 'especialidad').all())
        proyectistas_previa = await sync_to_async(_get_proyectistas)()
        proyectistas_actuales = LiquidacionEdificacionesResultBuilder.build_proyectistas_snapshot_data(
            proyectistas_previa
        )

        return NuevaRevisionFormularioResult(
            liquidacion_previa_id=str(liquidacion_previa_id),
            numero_revision=siguiente_numero,
            cobra=cobra,
            proyecto_id=str(previa.proyecto.id),
            proyecto_public_id=previa.proyecto.public_id or "",
            proyecto_nombre=previa.proyecto.denominacion,
            valor_proyecto=previa.valor_proyecto,
            valor_base_calculo=previa.valor_base_calculo if previa.valor_base_calculo is not None else previa.valor_proyecto,
            revisiones_vigentes=revisiones_vigentes,
            proyectistas_actuales=proyectistas_actuales,
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
            # Retornar estructura básica sin snapshot como dict — delega al builder
            return LiquidacionEdificacionesResultBuilder.build_result_from_liquidacion(
                liquidacion
            ).model_dump(mode="json")

        # Retornar el dict raw directamente — sin validación Pydantic
        # para preservar todos los campos almacenados (incluyendo _metadata y cualquier campo extra)
        return snapshot.data

    async def _get_municipalidad_model(self, municipalidad_id: str):
        """Obtiene modelo Municipalidad por ID."""
        from modules.entidades.models import Municipalidad
        return await sync_to_async(Municipalidad.objects.filter(id=municipalidad_id).first)()

    async def _validar_especialidades_exact_set(self, revisiones_data: list):
        """
        Valida que el conjunto de especialidades de las revisiones seleccionadas
        coincida exactamente con el conjunto de especialidades vigentes.

        Args:
            revisiones_data: Lista de revisiones (con .especialidad y .tarifa)

        Raises:
            EspecialidadesGrupoNoEncontradoError: Si no hay grupo de especialidades vigente
            EspecialidadesSetInvalidoError: Si los conjuntos no coinciden exactamente
        """
        from datetime import date
        from modules.liquidaciones.models import EdificacionesEspecialidades
        from ...exceptions import EspecialidadesGrupoNoEncontradoError, EspecialidadesSetInvalidoError

        today = date.today()

        # Buscar grupo de especialidades vigente para la fecha actual
        grupo_vigente = await sync_to_async(
            EdificacionesEspecialidades.objects.filter(
                periodo_inicio__lte=today
            ).filter(
                periodo_fin__isnull=True
            ).first
        )()

        if not grupo_vigente:
            raise EspecialidadesGrupoNoEncontradoError(
                f"No existe un grupo de especialidades vigente para la fecha {today}. "
                "Configure las especialidades de edificación antes de crear una liquidación."
            )

        # Obtener conjunto de especialidades del grupo vigente
        # NOTE: Must use sync_to_async for M2M access in async context
        def _sync_get_especialidades_grupo():
            return set(str(esp.id) for esp in grupo_vigente.especialidades.all())

        especialidades_grupo = await sync_to_async(_sync_get_especialidades_grupo)()

        # Extraer especialidades de las revisiones seleccionadas
        # Cada revisión puede tener M2M especialidades
        def _sync_get_especialidades_revisiones():
            result = set()
            for rev_data in revisiones_data:
                # Si la revisión tiene método especialidades (objeto ORM) o es result object
                if hasattr(rev_data, 'especialidades'):
                    # Es un objeto EdificacionesRevision del ORM
                    for esp in rev_data.especialidades.all():
                        result.add(str(esp.id))
                elif hasattr(rev_data, 'especialidad'):
                    # Es un result object con especialidad embebida
                    if hasattr(rev_data.especialidad, 'id'):
                        result.add(str(rev_data.especialidad.id))
            return result

        especialidades_revisiones = await sync_to_async(_sync_get_especialidades_revisiones)()

        # Validar conjunto exacto
        if especialidades_grupo != especialidades_revisiones:
            raise EspecialidadesSetInvalidoError(
                f"El conjunto de especialidades de las revisiones seleccionadas ({len(especialidades_revisiones)}) "
                f"no coincide exactamente con el grupo vigente ({len(especialidades_grupo)}). "
                f"Grupal: {especialidades_grupo}, Revisones: {especialidades_revisiones}. "
                "Las revisiones seleccionadas deben representar exactamente el mismo conjunto de especialidades."
            )

    async def _proceso_cotizar_primera_revision(
        self,
        proyecto_public_id: str,
        valor_proyecto: Decimal,
        valor_base_calculo: Decimal,
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
        revisiones_data = [self.core.to_revision_con_tarifa(rev) for rev in revisiones_data]

        # 4. Calcular — primera revisión siempre cobra
        # Usar valor_base_calculo para el cálculo
        cobra = True
        revision_results, subtotal, igv_monto, total_liquidacion = self.core.calcular_revisiones(
            valor_base_calculo=valor_base_calculo,
            revisiones_data=revisiones_data,
            cobra=cobra,
            igv_valor=variables.igv_valor,
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

        if len(revisiones_ids) != 1:
            from ...exceptions import RevisionesMultipleError
            raise RevisionesMultipleError(
                f"Se requiere exactamente UNA revisión para cotizar nueva revisión, pero se enviaron {len(revisiones_ids)}."
            )

        if not await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids):
            raise RevisionNoHabilitadaError(
                "Una o más revisiones seleccionadas no están habilitadas/vigentes"
            )

        revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 7. Determinar si cobra según número de revisión
        cobra = nuevo_numero in REVISIONES_COBRAN

        # 8. Obtener valor_proyecto y valor_base_calculo de la liquidación previa
        valor_proyecto = previa.valor_proyecto
        valor_base_calculo = previa.valor_base_calculo if previa.valor_base_calculo is not None else valor_proyecto

        # 9. Calcular usando valor_base_calculo
        revision_results, subtotal, igv_monto, total_liquidacion = self.core.calcular_revisiones(
            valor_base_calculo=valor_base_calculo,
            revisiones_data=revisiones_data,
            cobra=cobra,
            igv_valor=variables.igv_valor,
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

    # =============================================================================
    # Helper methods para validación y upsert de inline proyectistas/delegados
    # =============================================================================

    async def _validar_proyectistas_inline_cip(self, proyectistas_inline: list[ProyectistaInlineData]):
        """
        Valida TODOS los CIPs de los proyectistas inline antes de crear la liquidación.

        ALL-OR-NOTHING: Si cualquier CIP falla o no está habilitado, se rechaza toda la operación.

        Args:
            proyectistas_inline: Lista de ProyectistaInlineData con cip y especialidad_id

        Raises:
            CipNotFoundError: Si algún CIP no existe en el servicio externo
            CipServiceUnavailableError: Si el servicio CIP no está disponible
            BusinessError: Si algún ingeniero no está habilitado (condicion != '1')
        """
        from core.exceptions import CipNotFoundError
        from modules.usuarios.infrastructure.services import CipServiceUnavailableError
        from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData

        for p in proyectistas_inline:
            cip = p.cip
            if not cip:
                from ...exceptions import BusinessError
                raise BusinessError(f"CIP es requerido para cada proyectista")

            # Normalizar CIP
            normalized_cip = self._perfil_ingeniero_core._normalizar_cip(cip)
            if not normalized_cip:
                from ...exceptions import BusinessError
                raise BusinessError(f"CIP inválido: {cip}")

            # Llamar al cliente CIP
            try:
                raw_data = await sync_to_async(self._cip_client.get_colegiado)(normalized_cip)
            except CipServiceUnavailableError as e:
                raise

            if raw_data is None:
                raise CipNotFoundError(cip=normalized_cip)

            # Parsear a CipColegiadoData para acceso tipado
            cip_data = CipColegiadoData(**raw_data)

            # Validar que esté habilitado (condicion == '1')
            if not cip_data.habilitado:
                from ...exceptions import BusinessError
                raise BusinessError(
                    f"El ingeniero con CIP {normalized_cip} no está habilitado "
                    f"(condicion={cip_data.condicion}). Solo ingenieros habilitados pueden ser agregados."
                )

    def _upsert_proyectistas_inline(
        self,
        proyectistas_inline: list[ProyectistaInlineData],
        municipalidad_id: str,
    ) -> list[str]:
        """
        Crea/actualiza PerfilIngeniero y Proyectista para cada item inline.

        Dentro de transaction.atomic (ya abierto por el llamador).

        Args:
            proyectistas_inline: Lista de ProyectistaInlineData con cip, especialidad_id, descripcion
            municipalidad_id: ID de la municipalidad para buscar especialidad

        Returns:
            Lista de IDs de Proyectista creados/actualizados
        """
        from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData
        from modules.liquidaciones.domain.models import Especialidad

        proyectista_ids = []

        for p in proyectistas_inline:
            cip = p.cip
            especialidad_id = p.especialidad_id
            descripcion = p.descripcion

            # Normalizar CIP
            normalized_cip = self._perfil_ingeniero_core._normalizar_cip(cip)

            # Obtener datos del CIP (en este punto ya fueron validados)
            raw_data = self._cip_client.get_colegiado(normalized_cip)
            if not raw_data:
                from core.exceptions import CipNotFoundError
                raise CipNotFoundError(cip=normalized_cip)

            # Mapear a CipColegiadoData
            cip_data = CipColegiadoData(**raw_data)

            # Upsert PerfilIngeniero
            perfil, _ = self._perfil_ingeniero_core._upsert_perfil_from_cip(normalized_cip, cip_data)

            # Obtener especialidad
            try:
                especialidad = Especialidad.objects.get(id=especialidad_id)
            except Especialidad.DoesNotExist:
                from ...exceptions import NotFoundError
                raise NotFoundError(f"Especialidad con id={especialidad_id}")

            # Upsert Proyectista
            from modules.liquidaciones.domain.models import Proyectista
            proyectista, created = Proyectista.objects.update_or_create(
                perfil_ingeniero=perfil,
                especialidad=especialidad,
                defaults={'descripcion': descripcion or ''}
            )
            proyectista_ids.append(str(proyectista.id))

        return proyectista_ids

    async def _validar_delegados_ids(
        self,
        delegados_ids: list[str],
        municipalidad_id: str,
    ):
        """
        Valida que cada delegado exista, pertenezca a la municipalidad con categoria=Edificaciones y tenga periodo vigente.

        Args:
            delegados_ids: Lista de IDs de Delegado
            municipalidad_id: ID de la municipalidad

        Raises:
            NotFoundError: Si algún delegado no existe
            BusinessError: Si algún delegado no pertenece a la municipalidad como Edificaciones, no está activo o no tiene periodo vigente
        """
        from datetime import date
        from modules.liquidaciones.domain.models import Delegado, PeriodoDelegado, MunicipalidadDelegado
        from ...exceptions import NotFoundError, BusinessError

        today = date.today()

        for dele_id in delegados_ids:
            # Verificar que existe (usar select_related para evitar lazy loading en async context)
            try:
                delegado = await sync_to_async(
                    lambda: Delegado.objects.select_related('perfil_ingeniero').get(id=dele_id)
                )()
            except Delegado.DoesNotExist:
                raise NotFoundError(f"Delegado con id={dele_id}")

            # Verificar que pertenece a la municipalidad con categoria EDIFICACIONES
            from ...constants import CategoriaDelegado
            tiene_asignacion = await sync_to_async(
                lambda: (
                    MunicipalidadDelegado.objects
                    .filter(
                        delegado=delegado,
                        municipalidad_id=municipalidad_id,
                        activo=True,
                        categoria=CategoriaDelegado.EDIFICACIONES,
                    )
                    .exists()
                )
            )()
            if not tiene_asignacion:
                raise BusinessError(
                    f"El delegado {delegado.perfil_ingeniero.nombre_completo} "
                    f"no está asignado a la municipalidad {municipalidad_id} "
                    f"como delegado de Edificaciones"
                )

            # Verificar status activo
            if delegado.status != 'ACTIVO':
                raise BusinessError(
                    f"El delegado {delegado.perfil_ingeniero.nombre_completo} "
                    f"no está activo (status={delegado.status})"
                )

            # Verificar que tiene periodo vigente (periodo_fin=None significa abierto/vigente)
            from django.db.models import Q
            tiene_periodo = await sync_to_async(
                lambda: (
                    PeriodoDelegado.objects
                    .filter(
                        delegado=delegado,
                        periodo_inicio__lte=today,
                    )
                    .filter(
                        Q(periodo_fin__gte=today) | Q(periodo_fin__isnull=True)
                    )
                    .exists()
                )
            )()
            if not tiene_periodo:
                raise BusinessError(
                    f"El delegado {delegado.perfil_ingeniero.nombre_completo} "
                    f"no tiene un periodo vigente"
                )

    def _asociar_delegados(
        self,
        liq_edif: 'LiquidacionEdificaciones',
        delegados_ids: list[str],
    ):
        """
        Asocia delegados a la LiquidacionGeneral mediante LiquidacionDelegado.

        Dentro de transaction.atomic (ya abierto por el llamador).

        Args:
            liq_edif: Instancia de LiquidacionEdificaciones
            delegados_ids: Lista de IDs de Delegado
        """
        from modules.liquidaciones.domain.models import Delegado, LiquidacionDelegado

        for dele_id in delegados_ids:
            try:
                delegado = Delegado.objects.get(id=dele_id)
                LiquidacionDelegado.objects.create(
                    liquidacion=liq_edif.liquidacion,
                    delegado=delegado,
                )
            except Delegado.DoesNotExist:
                # Ya se validó antes, pero por seguridad verificamos
                pass

    def _crear_contactos_inline(
        self,
        liquidacion,
        contactos_inline: list[ContactoInlineData],
    ) -> None:
        """Crea Contacto nuevos y sus relaciones LiquidacionContacto."""
        from modules.entidades.models import Contacto
        from modules.liquidaciones.domain.models import LiquidacionContacto

        for data in contactos_inline:
            contacto = Contacto.objects.create(
                nombres=data.nombres,
                apellidos=data.apellidos,
                dni=data.dni,
                cargo=data.cargo,
                telefono=data.telefono,
                celular=data.celular,
                email=data.email,
                direccion=data.direccion,
            )
            LiquidacionContacto.objects.create(
                liquidacion=liquidacion,
                contacto=contacto,
                principal=data.principal,
                descripcion=data.descripcion,
            )

    async def _proceso_delegados_vigentes(
        self,
        municipalidad_id: str,
        revision_id: str | None = None,
        categoria: str | None = None,
    ) -> DelegadosVigentesResult:
        """
        Obtiene delegados vigentes para una municipalidad.

        1. Validar que la municipalidad exista
        2. Si categoria no se provee, usar Edificaciones por defecto
        3. Obtener delegados vigentes usando el core service (con filtro opcional por revision y categoria)
        4. Retornar DelegadosVigentesResult con lista tipada

        Args:
            municipalidad_id: UUID de la municipalidad
            revision_id: UUID opcional de EdificacionesRevision para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas). Default: Edificaciones

        Returns:
            DelegadosVigentesResult con lista de DelegadoVigenteResult:
            id, nombre_completo, cip, especialidad: {id, nombre}, tipo
        """
        from datetime import date
        from ...constants import CategoriaDelegado

        # 1. Validar municipalidad
        municipalidad = await self._get_municipalidad_model(municipalidad_id)
        if not municipalidad:
            from ...exceptions import NotFoundError
            raise NotFoundError(f"Municipalidad con id={municipalidad_id}")

        # 2. Si categoria no se provee, usar Edificaciones por defecto
        if not categoria:
            categoria = CategoriaDelegado.EDIFICACIONES

        # 3. Obtener delegados vigentes
        today = date.today()
        delegados = await sync_to_async(self.core._obtener_delegados_vigentes)(
            municipalidad_id=municipalidad_id,
            fecha=today,
            revision_id=revision_id,
            categoria=categoria,
        )

        return DelegadosVigentesResult(delegados=delegados)

    async def _proceso_especialidades_vigentes(self) -> list:
        """
        Obtiene las especialidades vigentes del grupo EdificacionesEspecialidades.

        Fuente: grupo EdificacionesEspecialidades cuyo periodo_inicio <= hoy
        y (periodo_fin IS NULL OR periodo_fin >= hoy).

        Returns:
            Lista de EspecialidadBasicaResult con id y nombre.
        """
        from datetime import date
        from django.db.models import Q
        from ...models import EdificacionesEspecialidades
        from ...schemas import EspecialidadBasicaResult

        today = date.today()

        # Obtener grupo de especialidades vigente
        grupo_vigente = EdificacionesEspecialidades.objects.filter(
            periodo_inicio__lte=today,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today)
        ).first()

        if not grupo_vigente:
            return []

        # Retornar especialidades del grupo vigente
        return [
            EspecialidadBasicaResult(id=esp.id, nombre=esp.nombre)
            for esp in grupo_vigente.especialidades.all()
        ]
