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
from ...schemas_proyecto import ProyectoInlineData
from modules.liquidaciones.models import LiquidacionEdificacion, LiquidacionPorcentajeObra, LiquidacionProyectista
from modules.liquidaciones.domain.constants import TramiteAccion
from modules.usuarios.infrastructure.services import ICipClient
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService


# Revisiones que cobran: 1, 3, 5
REVISIONES_COBRAN = {1, 3, 5}
MAX_REVISIONES = 5


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
        proyecto_public_id: str | None,
        municipalidad_id: str,
        tipo_tramite: str,
        valor_proyecto: Decimal,
        expediente: Optional[str],
        valor_base_calculo: Optional[Decimal],
        observacion: Optional[str],
        revisiones_ids: list[str],
        proyectistas_inline: Optional[list[ProyectistaInlineData]] = None,
        proyectistas_ids: Optional[list[str]] = None,
        # NOTE: delegados_ids fue eliminado de _proceso_primera_revision (Fase 4).
        # Los delegados se manejarán en un endpoint POST posterior separate.
        contactos_inline: Optional[list[ContactoInlineData]] = None,
        proyecto_inline: Optional[ProyectoInlineData] = None,
        tarifas_ids: Optional[list[str]] = None,
    ):
        """
        Proceso para crear primera revisión (nueva-liquidacion) de edificaciones.

        1. Obtener proyecto (inline o por public_id)
        2. Buscar municipalidad por ID
        3. Validar que no exista ya revisión 1 para ese proyecto
        4. Obtener IGV/UIT vigentes
        5. Validar revisiones seleccionadas están vigentes/habilitadas
        6. Si hay proyectistas_inline (inline con CIP):
           - Validar TODOS los CIPs via servicio externo (ALL-OR-NOTHING)
           - Si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        7. Validar delegados (si se proveen)
        8. Crear LiquidacionGeneral (con municipalidad y public_id)
        9. Crear LiquidacionEdificacion con proyectistas upsertados
        10. Asociar revisiones y delegados
        11. Calcular por cada revisión
        12. Crear snapshot
        13. Retornar resultado
        """
        # 1. Obtener proyecto (inline o por public_id)
        # XOR ya validado en orchestrator: exactamente uno de los dos está presente
        if proyecto_inline:
            # Crear proyecto inline dentro de la transacción
            proyecto = await sync_to_async(self.core._crear_proyecto_inline)(proyecto_inline)
        else:
            # Buscar proyecto existente por public_id
            proyecto = await sync_to_async(self.core._obtener_proyecto_por_public_id)(proyecto_public_id)
            if not proyecto:
                raise ProyectoNotFoundError(f"Proyecto con public_id={proyecto_public_id}")

        # 2. Buscar municipalidad
        municipalidad = await self._get_municipalidad_model(municipalidad_id)
        if not municipalidad:
            from ...exceptions import NotFoundError
            raise NotFoundError(f"Municipalidad con id={municipalidad_id}")

        # ── Fase 3: Validar tarifas_ids (exactamente 1 elemento) ──────────────
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            from ...exceptions import BusinessError
            raise BusinessError(
                f"tarifas_ids debe contener exactamente 1 elemento para primera revisión, "
                f"pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Validar que la tarifa exista, esté vigente, sea EDIFICACION, tenga detalle,
        # tenga al menos una especialidad asociada, y tenga ReglaTarifaEdificacion
        # para tipo_tramite y tramite_accion.
        tarifas_validadas = []
        if tarifas_ids is not None:
            tarifas_validadas = await sync_to_async(self.core._validar_tarifa_por_tipo_tramite)(
                tarifas_ids,
                tipo_tramite=tipo_tramite,
                tramite_accion=TramiteAccion.PRIMERA_REVISION,
            )
        # ── Fin Fase 3 ───────────────────────────────────────────────────────────

        # 3. Validar que no exista primera revisión
        if await sync_to_async(self.core._existe_primera_revision_proyecto)(proyecto.id):
            raise PrimeraRevisionYaExisteError(
                f"Ya existe una primera revisión para el proyecto {proyecto_public_id}"
            )

        # 4. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # 5. Validar revisiones seleccionadas están vigentes/habilitadas
        if revisiones_ids:
            try:
                habilitada = await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids)
            except ValueError as e:
                from ...exceptions import RevisionIdsInvalidosError
                raise RevisionIdsInvalidosError(str(e))
            if not habilitada:
                raise RevisionNoHabilitadaError(
                    "Una o más revisiones seleccionadas no están habilitadas/vigentes"
                )

        # Obtener datos de revisiones
        if not revisiones_ids:
            if tarifas_ids is not None:
                # Fase 3: usar la tarifa seleccionada específicamente (ya validada en paso anterior)
                # _obtener_revisiones_por_ids retorna EdificacionRevisionData con especialidades y tarifa
                revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(tarifas_ids)
            else:
                # Auto-selección: todas las activas de EDIFICACION
                revisiones_data = await sync_to_async(self.core._obtener_revisiones_vigentes_result)()
                # Transformar RevisionVigenteResult (flat) a estructura anidada con .tarifa y .especialidad
                revisiones_data = [self.core.to_revision_con_tarifa(rev) for rev in revisiones_data]
        else:
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 5b. Validar exact-set de especialidades vigentes (primera revisión)
        # NOTA: Cuando tarifas_ids es proporcionado explícitamente, se salta esta validación
        # porque el usuario ya seleccionó una tarifa específica (no quiere auto-selección).
        if tarifas_ids is None:
            await self._validar_especialidades_exact_set(revisiones_data)

        # 6. Si hay proyectistas_inline (inline con CIP), validar TODOS los CIPs
        # ALL-OR-NOTHING: si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        if proyectistas_inline:
            await self._validar_proyectistas_inline_cip(proyectistas_inline)

        # NOTE: Validación y asociación de delegados fue eliminada de _proceso_primera_revision (Fase 4).
        # Los delegados se manejarán en un endpoint POST posterior separate.

        # 5-8. Crear liquidación y calcular
        # Primera revisión siempre cobra
        cobra = True

        # Validar valor_base_calculo según tipo_tramite
        from ...validators import validate_valor_base_calculo
        validate_valor_base_calculo(
            valor_proyecto=valor_proyecto,
            valor_base_calculo=valor_base_calculo if valor_base_calculo is not None else valor_proyecto,
            tipo_tramite=tipo_tramite,
        )

        # Ejecutar bloque transactional en thread async
        def _run_primera_revision():
            from django.db import transaction
            from modules.liquidaciones.models import TarifaPorcentajeObra, LiquidacionPorcentajeObra

            with transaction.atomic():
                # Crear LiquidacionGeneral con numero_revision=1 (fuente de verdad)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    expediente=expediente,
                    observacion=observacion,
                    liquidacion_previa=None,
                    numero_revision=1,
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

                # Crear LiquidacionEdificacion (sin numero_revision — vive en LiquidacionGeneral)
                # Nota: valor_proyecto y valor_base_calculo viven en LiquidacionPorcentajeObra, no aquí
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    tipo_tramite=tipo_tramite,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                    proyectistas_ids=final_proyectistas_ids,
                )

                # NOTE: Asociación de delegados fue eliminada de _proceso_primera_revision (Fase 4).
                # Los delegados se manejarán en un endpoint POST posterior separate.

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

                # 8b. Persistir LiquidacionPorcentajeObra por cada revisión calculada
                # El cálculo se persistía solo en el snapshot — ahora también en la tabla
                valor_base = valor_base_calculo if valor_base_calculo is not None else valor_proyecto
                for rev in revision_results:
                    # Obtener la tarifa porcentual (TarifaPorcentajeObra) desde el resultado del cálculo
                    # rev.tarifa.id es el ID de TarifaPorcentajeObra
                    try:
                        tarifa_pct = TarifaPorcentajeObra.objects.get(id=rev.tarifa.id)
                    except TarifaPorcentajeObra.DoesNotExist:
                        # Si no se encuentra, saltar — la tarifa puede no existir en el nuevo diseño
                        continue
                    LiquidacionPorcentajeObra.objects.create(
                        liquidacion_general=liquidacion,
                        valor_proyecto=valor_proyecto,
                        valor_base_calculo=valor_base,
                        tarifa_aplicada=tarifa_pct,
                    )

                # 8c. Guardar sub_total en LiquidacionGeneral
                liquidacion.sub_total = subtotal
                liquidacion.save(update_fields=['sub_total'])

                # 9. Construir resultado — delega al builder (dentro del contexto sync)
                # Pre-materializar proyectistas antes de retornar para evitar acceso ORM en contexto async
                # Refactor: usar LiquidacionProyectista en lugar de M2M en LiquidacionEdificacion
                edificaciones_proyectistas = [
                    lp.proyectista for lp in LiquidacionProyectista.objects.filter(
                        liquidacion_general=liq_edif.liquidacion
                    ).select_related('proyectista__perfil_ingeniero', 'proyectista__especialidad')
                ]
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
        tarifas_ids: Optional[list[str]] = None,
    ):
        """
        Proceso para crear nueva revisión de edificaciones.

        Secuencia de revisiones: 1 -> 3 -> 5 (solo números impares, paso +2).
        No se pueden crear revisiones 2, 4, 6, 7.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular nuevo numero_revision = previa.numero_revision + 2 (paso +2)
        4. Validar <= 5 y que no exista ya esa revisión
        5. Determinar si cobra según número de revisión
        6. Validar tarifas_ids (exactamente 1 elemento si se provee)
        7. Validar revisiones seleccionadas existen y habilitadas
        8. Si hay proyectistas_inline (inline con CIP):
           - Validar TODOS los CIPs via servicio externo (ALL-OR-NOTHING)
           - Si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        9. Determinar proyectistas:
           - Si se proporcionó y no está vacío, usar esos (inline o IDs)
           - Si se omitió o está vacío, heredar de la liquidación previa
        10. Validar delegados (si se proveen, o heredar si se omiten)
        11. Crear LiquidacionGeneral y LiquidacionEdificaciones
        12. Si no cobra: cálculos en 0 pero conservar estructura
        13. Si cobra: calcular con porcentajes
        14. Guardar snapshot
        15. Retornar resultado
        """
        # 1. Buscar liquidación previa
        previa = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_previa_id)
        if not previa:
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_previa_id}")

        # 2. Validar que sea de edificaciones
        def _get_liq_edif_previa():
            return LiquidacionEdificacion.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificacion.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular nuevo número desde LiquidacionGeneral (fuente de verdad)
        # Secuencia: 1 -> 3 -> 5 (paso +2)
        nuevo_numero = previa.numero_revision + 2

        # 4. Validar <= 5 y no exista
        if nuevo_numero > MAX_REVISIONES:
            raise MaximoRevisionAlcanzadoError(
                f"No se puede crear más de {MAX_REVISIONES} revisiones. "
                f"La revisión {nuevo_numero} excede el máximo permitido."
            )
        if await sync_to_async(self.core._existe_revision_numero_proyecto)(previa.proyecto_id, nuevo_numero):
            from ...exceptions import ConflictError
            raise ConflictError(
                f"Ya existe la revisión {nuevo_numero} para este proyecto"
            )

        # 5. Determinar si cobra
        cobra = nuevo_numero in REVISIONES_COBRAN

        # 6. Validar tarifas_ids (exactamente 1 elemento si se provee)
        # Las tarifas se validan con tipo_tramite de la liquidación previa y TramiteAccion.REVISION
        tipo_tramite_previo = liq_edif_previa.tipo_tramite
        tarifas_validadas = []
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            from ...exceptions import BusinessError
            raise BusinessError(
                f"tarifas_ids debe contener exactamente 1 elemento para nueva revisión, "
                f"pero se recibieron {len(tarifas_ids)} elementos."
            )
        if tarifas_ids is not None:
            tarifas_validadas = await sync_to_async(self.core._validar_tarifa_por_tipo_tramite)(
                tarifas_ids,
                tipo_tramite=tipo_tramite_previo,
                tramite_accion=TramiteAccion.REVISION,
            )

        # 7. Validar revisiones seleccionadas - exactamente UNA para nueva revisión
        if revisiones_ids:
            if len(revisiones_ids) != 1:
                from ...exceptions import RevisionesMultipleError
                raise RevisionesMultipleError(
                    f"Se requiere exactamente UNA revisión para nueva revisión, pero se enviaron {len(revisiones_ids)}."
                )
            try:
                habilitada = await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids)
            except ValueError as e:
                from ...exceptions import RevisionIdsInvalidosError
                raise RevisionIdsInvalidosError(str(e))
            if not habilitada:
                raise RevisionNoHabilitadaError(
                    "Una o más revisiones seleccionadas no están habilitadas/vigentes"
                )

        # Obtener datos de revisiones
        if not revisiones_ids:
            if tarifas_ids is not None:
                # Usar la tarifa seleccionada específicamente
                revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(tarifas_ids)
            else:
                # Auto-selección: error si no se provee tarifas_ids
                from ...exceptions import BusinessError
                raise BusinessError(
                    "tarifas_ids es requerido para nueva revisión. "
                    "No se permite auto-selección de tarifas."
                )
        else:
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # Obtener valor_proyecto y valor_base_calculo de LiquidacionPorcentajeObra de la liquidación previa
        # valor_base_calculo se hereda de la liquidación previa para mantener consistencia
        lpo_previa = await sync_to_async(
            lambda: liq_edif_previa.liquidacion.liquidacion_porcentaje_obra.first()
        )()
        valor_proyecto = lpo_previa.valor_proyecto if lpo_previa else Decimal('0')
        valor_base_calculo = lpo_previa.valor_base_calculo if lpo_previa and lpo_previa.valor_base_calculo is not None else valor_proyecto

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
            # Heredar de la liquidación previa (usando LiquidacionProyectista)
            final_proyectistas_ids = await sync_to_async(lambda: list(
                LiquidacionProyectista.objects.filter(
                    liquidacion_general=liq_edif_previa.liquidacion
                ).values_list('proyectista_id', flat=True)
            ))()
            final_delegados_ids = None  # Se heredarán dentro de la transacción si no se especifican

        # 8. Validar/modificar delegados si se proveen
        if delegados_ids:
            await self._validar_delegados_ids(delegados_ids, str(previa.municipalidad_id))
        elif final_delegados_ids is None:
            # Heredar delegados de la liquidación previa si no se especificaron
            final_delegados_ids = await sync_to_async(lambda: list(
                liq_edif_previa.liquidacion.liquidacion_delegados.values_list('delegado_id', flat=True)
            ))()

        # Ejecutar bloque transactional en thread async
        def _run_nueva_revision():
            nonlocal final_proyectistas_ids
            from django.db import transaction
            from modules.liquidaciones.models import TarifaPorcentajeObra, LiquidacionPorcentajeObra

            with transaction.atomic():
                # 8. Crear/upsertear proyectistas desde inline data si existe
                if proyectistas_inline:
                    final_proyectistas_ids = self._upsert_proyectistas_inline(
                        proyectistas_inline, str(previa.municipalidad_id)
                    )

                # 9. Crear LiquidacionGeneral con numero_revision (fuente de verdad)
                liquidacion = self.core._crear_liquidacion_general(
                    proyecto=previa.proyecto,
                    municipalidad=previa.municipalidad,
                    expediente=None,
                    observacion=observacion,
                    liquidacion_previa=previa,
                    numero_revision=nuevo_numero,
                )

                # 10. Crear LiquidacionEdificaciones (sin numero_revision — vive en LiquidacionGeneral)
                # Nota: valor_proyecto y valor_base_calculo ya NO se pasan — viven en LiquidacionPorcentajeObra
                liq_edif = self.core._crear_liquidacion_edificaciones(
                    liquidacion=liquidacion,
                    tipo_tramite=liq_edif_previa.tipo_tramite,  # Heredado de la liquidación previa
                    tramite_accion=TramiteAccion.REVISION,
                    proyectistas_ids=final_proyectistas_ids,
                )

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

                # 10b. Persistir LiquidacionPorcentajeObra por cada revisión calculada
                # El cálculo se persistía solo en el snapshot — ahora también en la tabla
                for rev in revision_results:
                    # Obtener la tarifa porcentual (TarifaPorcentajeObra) desde el resultado del cálculo
                    # rev.tarifa.id es el ID de TarifaPorcentajeObra
                    try:
                        tarifa_pct = TarifaPorcentajeObra.objects.get(id=rev.tarifa.id)
                    except TarifaPorcentajeObra.DoesNotExist:
                        # Si no se encuentra, saltar — la tarifa puede no existir en el nuevo diseño
                        continue
                    LiquidacionPorcentajeObra.objects.create(
                        liquidacion_general=liquidacion,
                        valor_proyecto=valor_proyecto,
                        valor_base_calculo=valor_base_calculo,
                        tarifa_aplicada=tarifa_pct,
                    )

                # 10c. Guardar sub_total en LiquidacionGeneral
                liquidacion.sub_total = subtotal
                liquidacion.save(update_fields=['sub_total'])

                # 11. Construir resultado — delega al builder (dentro del contexto sync)
                # Pre-materializar proyectistas antes de retornar para evitar acceso ORM en contexto async
                # Refactor: usar LiquidacionProyectista en lugar de M2M en LiquidacionEdificacion
                edificaciones_proyectistas = [
                    lp.proyectista for lp in LiquidacionProyectista.objects.filter(
                        liquidacion_general=liq_edif.liquidacion
                    ).select_related('proyectista__perfil_ingeniero', 'proyectista__especialidad')
                ]
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

        Secuencia de revisiones: 1 -> 3 -> 5 (solo números impares, paso +2).
        No se pueden crear revisiones 2, 4, 6, 7.

        1. Buscar liquidación previa
        2. Validar que sea de edificaciones
        3. Calcular siguiente número de revisión (previa + 2)
        4. Determinar si cobrará
        5. Obtener tarifas disponibles filtradas por tipo_tramite + REVISION
        6. Obtener proyectistas actuales (heredados de la liquidación previa)
        7. Obtener contactos de la liquidación previa
        8. Retornar datos del formulario
        """
        # 1. Buscar liquidación previa
        previa = await sync_to_async(self.core._obtener_liquidacion_por_id)(liquidacion_previa_id)
        if not previa:
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_previa_id}")

        # 2. Validar que sea de edificaciones
        def _get_liq_edif_previa():
            return LiquidacionEdificacion.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificacion.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular siguiente número desde LiquidacionGeneral (fuente de verdad)
        # Secuencia: 1 -> 3 -> 5 (paso +2)
        siguiente_numero = previa.numero_revision + 2

        if siguiente_numero > MAX_REVISIONES:
            raise MaximoRevisionAlcanzadoError(
                f"No se puede crear más de {MAX_REVISIONES} revisiones. "
                f"La revisión {siguiente_numero} excede el máximo permitido."
            )

        # 4. Determinar si cobrará
        cobra = siguiente_numero in REVISIONES_COBRAN

        # 5. Obtener tarifas disponibles filtradas por tipo_tramite + REVISION
        # El tipo_tramite viene de la liquidación previa
        tipo_tramite_previo = liq_edif_previa.tipo_tramite
        tarifas_disponibles = await sync_to_async(self.core._obtener_revisiones_vigentes_result)(
            tipo_tramite=tipo_tramite_previo,
            tramite_accion=TramiteAccion.REVISION,
        )

        # 6. Obtener proyectistas actuales (heredados de la liquidación previa)
        # Delegar construcción de ProyectistaEdificacionData al builder para
        # mantener el flujo enfocado en coordinación de pasos de negocio.
        # El builder recibe instancias ORM y produce domain DTOs (ProyectistaEdificacionData).
        def _get_proyectistas():
            # Refactor: usar LiquidacionProyectista en lugar de M2M en LiquidacionEdificacion
            return [lp.proyectista for lp in LiquidacionProyectista.objects.filter(
                liquidacion_general=liq_edif_previa.liquidacion
            ).select_related('proyectista__perfil_ingeniero', 'proyectista__especialidad')]
        proyectistas_previa = await sync_to_async(_get_proyectistas)()
        proyectistas_actuales = LiquidacionEdificacionesResultBuilder.build_proyectistas_data(
            proyectistas_previa
        )

        # 7. Obtener contactos de la liquidación previa
        def _get_contactos():
            from modules.liquidaciones.models import LiquidacionContacto
            return list(LiquidacionContacto.objects.filter(
                liquidacion=liq_edif_previa.liquidacion
            ).select_related('contacto').all())
        contactos_previa = await sync_to_async(_get_contactos)()

        # Obtener valor_proyecto y valor_base_calculo de LiquidacionPorcentajeObra de la liquidación previa
        def _get_lpo_previa():
            return liq_edif_previa.liquidacion.liquidacion_porcentaje_obra.first()
        lpo_previa = await sync_to_async(_get_lpo_previa)()
        vp = lpo_previa.valor_proyecto if lpo_previa else Decimal('0')
        vbc = lpo_previa.valor_base_calculo if lpo_previa and lpo_previa.valor_base_calculo is not None else vp

        return NuevaRevisionFormularioResult(
            liquidacion_previa_id=str(liquidacion_previa_id),
            numero_revision=siguiente_numero,
            cobra=cobra,
            proyecto_id=str(previa.proyecto.id),
            proyecto_public_id=previa.proyecto.public_id or "",
            proyecto_nombre=previa.proyecto.denominacion,
            valor_proyecto=vp,
            valor_base_calculo=vbc,
            revisiones_vigentes=tarifas_disponibles,
            proyectistas_actuales=proyectistas_actuales,
            tipo_tramite=tipo_tramite_previo,
        )

    async def _get_municipalidad_model(self, municipalidad_id: str):
        """Obtiene modelo Municipalidad por ID."""
        from modules.entidades.models import Municipalidad
        return await sync_to_async(Municipalidad.objects.filter(id=municipalidad_id).first)()

    async def _validar_especialidades_exact_set(self, revisiones_data: list):
        """
        Valida que el conjunto de especialidades de las revisiones seleccionadas
        coincida exactamente con el conjunto de especialidades vigentes.

        La validación hace la UNIÓN de todas las especialidades M2M de las revisiones
        seleccionadas y la compara con el grupo vigente de EspecialidadesLiquidacion.

        Args:
            revisiones_data: Lista de revisiones (con .especialidad y, opcionalmente, .especialidades)

        Raises:
            EspecialidadesGrupoNoEncontradoError: Si no hay grupo de especialidades vigente
            EspecialidadesSetInvalidoError: Si los conjuntos no coinciden exactamente
        """
        from datetime import date
        from modules.liquidaciones.models import EspecialidadesLiquidacion
        from ...constants import TipoLiquidacion
        from ...exceptions import EspecialidadesGrupoNoEncontradoError, EspecialidadesSetInvalidoError

        today = date.today()

        # Buscar grupo de especialidades vigente para EDIFICACION usando EspecialidadesLiquidacion
        grupo_vigente = await sync_to_async(
            EspecialidadesLiquidacion.objects.filter(
                tipo_liquidacion=TipoLiquidacion.EDIFICACION,
                periodo_inicio__lte=today,
            ).filter(
                periodo_fin__isnull=True
            ).first
        )()

        if not grupo_vigente:
            raise EspecialidadesGrupoNoEncontradoError(
                f"No existe un grupo de especialidades vigente para la fecha {today}. "
                "Configure las especialidades de edificación antes de crear una liquidación."
            )

        # Obtener conjunto de especialidades del grupo vigente con nombres para mensajes
        def _sync_get_especialidades_grupo():
            return {(str(esp.id), esp.nombre) for esp in grupo_vigente.especialidades.all()}

        grupo_con_nombres = await sync_to_async(_sync_get_especialidades_grupo)()
        especialidades_grupo = {id_ for id_, _ in grupo_con_nombres}
        grupo_nombres = {nombre for _, nombre in grupo_con_nombres}

        # Extraer especialidades de las revisiones seleccionadas (UNIÓN de todas)
        # Cada revisión puede tener M2M especialidades
        def _sync_get_especialidades_revisiones():
            result = set()  # (id, nombre)
            nombres_revisiones = set()
            for rev_data in revisiones_data:
                # Caso 1: EdificacionRevisionData con campo `especialidades` (lista de EspecialidadData)
                if hasattr(rev_data, 'especialidades') and rev_data.especialidades is not None:
                    for esp in rev_data.especialidades:
                        result.add((str(esp.id), esp.nombre))
                        nombres_revisiones.add(esp.nombre)
                # Caso 2: ORM object TarifaLiquidacionBase con M2M .especialidades.all()
                elif hasattr(rev_data, 'especialidades') and callable(rev_data.especialidades.all):
                    for esp in rev_data.especialidades.all():
                        result.add((str(esp.id), esp.nombre))
                        nombres_revisiones.add(esp.nombre)
                # Caso 3: result object sin `especialidades` — usar `especialidad` singular (retrocompatibilidad)
                elif hasattr(rev_data, 'especialidad') and hasattr(rev_data.especialidad, 'id'):
                    result.add((str(rev_data.especialidad.id), rev_data.especialidad.nombre))
                    nombres_revisiones.add(rev_data.especialidad.nombre)
            return result, nombres_revisiones

        result_tuple = await sync_to_async(_sync_get_especialidades_revisiones)()
        especialidades_revisiones, nombres_revisiones = result_tuple
        especialidades_revisiones_ids = {id_ for id_, _ in especialidades_revisiones}

        # Validar conjunto exacto
        if especialidades_grupo != especialidades_revisiones_ids:
            missing_ids = especialidades_grupo - especialidades_revisiones_ids
            extra_ids = especialidades_revisiones_ids - especialidades_grupo

            detail_parts = []
            if missing_ids:
                missing_nombres = [nombre for id_, nombre in grupo_con_nombres if id_ in missing_ids]
                detail_parts.append(
                    f"Faltan especialidades en selecciones: {missing_ids} ({missing_nombres})"
                )
            if extra_ids:
                extra_nombres = [nombre for id_, nombre in especialidades_revisiones if id_ in extra_ids]
                detail_parts.append(
                    f"Especialidades extra/no vigentes en selecciones: {extra_ids} ({extra_nombres})"
                )

            raise EspecialidadesSetInvalidoError(
                f"El conjunto de especialidades de las revisiones seleccionadas "
                f"no coincide exactamente con el grupo vigente.\n"
                f"Grupo vigente ({len(especialidades_grupo)}): {sorted(grupo_nombres)}\n"
                f"Selecciones ({len(especialidades_revisiones_ids)}): {sorted(nombres_revisiones)}\n"
                + "\n".join(detail_parts) +
                "\nLas revisiones seleccionadas deben cubrir TODAS las especialidades del grupo "
                "y NINGUNA más. Si ve IDs que no reconoce, verifique que está enviando "
                "IDs de TarifaLiquidacionBase, no IDs de Especialidad."
            )

    async def _proceso_cotizar_primera_revision(
        self,
        tipo_tramite: str | None,
        valor_proyecto: Decimal,
        valor_base_calculo: Optional[Decimal],
        tarifas_ids: Optional[list[str]] = None,
    ) -> CotizacionQuoteData:
        """
        Cotiza primera revisión sin guardar en BD.

        1. Obtener IGV/UIT vigentes
        2. Fase 3: Si tarifas_ids tiene exactamente 1 elemento, usar esa tarifa específica.
           Caso contrario, obtener revisiones vigentes filtradas por EDIFICACION (auto-selección).
        3. Calcular con cobra=True (primera siempre cobra)
        4. Retornar resultado de cotización

        No crea ningún registro en BD.
        
        Nota: La cotización es específica para Edificación — no depende de proyecto_public_id
        ya que el cálculo solo usa valores y tarifas de Edificación (TarifaLiquidacionBase
        filtrada por tipo_liquidacion=EDIFICACION).
        
        Args:
            tipo_tramite: Tipo de trámite de edificación (requerido si tarifas_ids es proporcionado).
            valor_proyecto: Valor del proyecto/obra.
            valor_base_calculo: Valor base de cálculo.
            tarifas_ids: Lista de IDs de tarifas a usar (exactamente 1 elemento para Fase 3).
        """
        # 1. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()

        # 2. Fase 3: Obtener revisiones
        if tarifas_ids is not None:
            # Validar exactamente 1 elemento
            if len(tarifas_ids) != 1:
                from ...exceptions import BusinessError
                raise BusinessError(
                    f"tarifas_ids debe contener exactamente 1 elemento para cotización, "
                    f"pero se recibieron {len(tarifas_ids)} elementos."
                )
            # Cuando se provee tarifas_ids, tipo_tramite es requerido para validar la ReglaTarifaEdificacion
            if tipo_tramite is None:
                from ...exceptions import BusinessError
                raise BusinessError(
                    "tipo_tramite es requerido cuando se provee tarifas_ids. "
                    "Proporcione el tipo de trámite de edificación (OBRA_NUEVA, DEMOLICION, AMPLIACION, etc.)."
                )
            # Validar y usar la tarifa seleccionada específicamente (incluye verificar que tenga especialidades
            # y que tenga ReglaTarifaEdificacion para tipo_tramite + PRIMERA_REVISION)
            await sync_to_async(self.core._validar_tarifa_por_tipo_tramite)(
                tarifas_ids,
                tipo_tramite=tipo_tramite,
                tramite_accion=TramiteAccion.PRIMERA_REVISION,
            )
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(tarifas_ids)
        else:
            # Auto-selección: todas las activas de EDIFICACION
            revisiones_data = await sync_to_async(self.core._obtener_revisiones_vigentes_result)()
            # Transformar RevisionVigenteResult (flat) a estructura anidada con .tarifa y .especialidad
            revisiones_data = [self.core.to_revision_con_tarifa(rev) for rev in revisiones_data]

        # 3. Calcular — primera revisión siempre cobra
        # Si valor_base_calculo es None, usar valor_proyecto
        valor_base = valor_base_calculo if valor_base_calculo is not None else valor_proyecto
        cobra = True
        revision_results, subtotal, igv_monto, total_liquidacion = self.core.calcular_revisiones(
            valor_base_calculo=valor_base,
            revisiones_data=revisiones_data,
            cobra=cobra,
            igv_valor=variables.igv_valor,
        )

        # 4. Retornar resultado de cotización
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
                valor_base_calculo=valor_base,
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
            return LiquidacionEdificacion.objects.select_related('liquidacion').get(liquidacion=previa)
        try:
            liq_edif_previa = await sync_to_async(_get_liq_edif_previa)()
        except LiquidacionEdificacion.DoesNotExist:
            raise TipoLiquidacionInvalidoError(
                "La liquidación previa no es de tipo edificaciones"
            )

        # 3. Calcular siguiente número desde LiquidacionGeneral (fuente de verdad)
        nuevo_numero = previa.numero_revision + 1

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

        try:
            habilitada = await sync_to_async(self.core._todas_revisiones_habilitadas)(revisiones_ids)
        except ValueError as e:
            from ...exceptions import RevisionIdsInvalidosError
            raise RevisionIdsInvalidosError(str(e))
        if not habilitada:
            raise RevisionNoHabilitadaError(
                "Una o más revisiones seleccionadas no están habilitadas/vigentes"
            )

        revisiones_data = await sync_to_async(self.core._obtener_revisiones_por_ids)(revisiones_ids)

        # 7. Determinar si cobra según número de revisión
        cobra = nuevo_numero in REVISIONES_COBRAN

        # 8. Obtener valor_proyecto y valor_base_calculo de LiquidacionPorcentajeObra de la liquidación previa
        def _get_lpo_previa():
            return liq_edif_previa.liquidacion.liquidacion_porcentaje_obra.first()
        lpo_previa = await sync_to_async(_get_lpo_previa)()
        valor_proyecto = lpo_previa.valor_proyecto if lpo_previa else Decimal('0')
        valor_base_calculo = lpo_previa.valor_base_calculo if lpo_previa and lpo_previa.valor_base_calculo is not None else valor_proyecto

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
                valor_base_calculo=valor_base_calculo,
            ),
        )

    # === Métodos públicos para orchestrator (delegación) ===

    async def listar_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
        proyecto_public_id: str | None = None,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas — delega a core via sync_to_async."""
        return await sync_to_async(self.core._listar_liquidaciones_paginado_result)(page, page_size, proyecto_public_id)

    async def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str | None = None,
    ) -> list[RevisionVigenteResult]:
        """
        Obtiene las revisiones vigentes — delega a core via sync_to_async.

        Si tipo_tramite y tramite_accion son provistos, filtra usando ReglaTarifaEdificacion.
        """
        return await sync_to_async(self.core._obtener_revisiones_vigentes_result)(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )

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
        liq_edif: 'LiquidacionEdificacion',
        delegados_ids: list[str],
    ):
        """
        Asocia delegados a la LiquidacionGeneral mediante LiquidacionDelegado.

        Dentro de transaction.atomic (ya abierto por el llamador).

        Args:
            liq_edif: Instancia de LiquidacionEdificacion
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
            revision_id: UUID opcional de TarifaLiquidacionBase para filtrar por especialidades
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
        Obtiene las especialidades vigentes del grupo EspecialidadesLiquidacion.

        Fuente: grupo EspecialidadesLiquidacion cuyo tipo_liquidacion=EDIFICACION,
        periodo_inicio <= hoy y (periodo_fin IS NULL OR periodo_fin >= hoy).

        Returns:
            Lista de EspecialidadBasicaResult con id y nombre.
        """
        from datetime import date
        from django.db.models import Q
        from ...models import EspecialidadesLiquidacion
        from ...constants import TipoLiquidacion
        from ...schemas import EspecialidadBasicaResult

        today = date.today()

        # Obtener grupo de especialidades vigente para EDIFICACION usando EspecialidadesLiquidacion
        grupo_vigente = EspecialidadesLiquidacion.objects.filter(
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
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

    async def _proceso_obtener_liquidacion_edificacion_detalle(
        self,
        liquidacion_id: str,
    ):
        """
        Obtiene una liquidación de edificación por ID para retornar en GET /{id}.

        1. Obtener liquidación con todos los datos relacionados (core)
        2. Reconstruir revision_results desde LiquidacionPorcentajeObra
        3. Construir LiquidacionEdificacionesResult via builder
        4. Retornar resultado plano para presenter
        """
        # Obtener datos crudos del core
        data = await sync_to_async(self.core._obtener_liquidacion_edificacion_para_detalle)(liquidacion_id)
        if not data:
            from ...exceptions import LiquidacionNotFoundError
            raise LiquidacionNotFoundError(f"Liquidacion with id={liquidacion_id}")

        liquidacion = data['liquidacion']
        proyecto = data['proyecto']
        revision_raw = data['revision_results']
        subtotal = data['subtotal']
        igv_monto = data['igv_monto']
        total_liquidacion = data['total_liquidacion']
        total_a_pagar = data['total_a_pagar']
        variables = data['variables']
        cobra = data['cobra']
        liq_edif = data['liq_edif']
        edificaciones_proyectistas = data['edificaciones_proyectistas']
        edificaciones_delegados = data['edificaciones_delegados']
        contactos_orm = data['contactos_orm']
        valor_proyecto = data['valor_proyecto']

        # Reconstruir revision_results como objetos con la estructura que espera el builder
        revision_results = []
        from ...schemas import RevisionConTarifaData, TarifaCalculoData, EspecialidadBasicaResult

        for rev in revision_raw:
            # Construir especialidades como objetos con atributos
            especialidades_objs = [
                type('Esp', (), {'id': e['id'], 'nombre': e['nombre']})()
                for e in rev.get('especialidades', [])
            ]

            # Construir tarifa como objeto con atributos
            tarifa_data = rev.get('tarifa', {})
            tarifa_obj = type('Tarifa', (), {
                'id': tarifa_data.get('id', ''),
                'derecho_minimo': Decimal(str(tarifa_data.get('derecho_minimo', 0))),
                'derecho_maximo': Decimal(str(tarifa_data['derecho_maximo'])) if tarifa_data.get('derecho_maximo') else None,
                'porcentaje_minimo_uit': Decimal(str(tarifa_data.get('porcentaje_minimo_uit', 0))),
            })()

            # Construir revision con atributos
            revision_results.append(type('Revision', (), {
                'id': rev.get('id', ''),
                'numero_revision': rev.get('numero_revision', 1),
                'tarifa': tarifa_obj,
                'especialidades': especialidades_objs,
                'especialidad_nombre': rev.get('especialidad_nombre', ''),
                'monto_base': Decimal(str(rev.get('monto_base', 0))),
                'cobra': rev.get('cobra', False),
            })())

        # Construir resultado usando el builder
        from ..builders import LiquidacionEdificacionesResultBuilder
        result = LiquidacionEdificacionesResultBuilder.build_result(
            liquidacion=liquidacion,
            proyecto=proyecto,
            revision_results=revision_results,
            subtotal=subtotal,
            igv_monto=igv_monto,
            total_liquidacion=total_liquidacion,
            total_a_pagar=total_a_pagar,
            variables=variables,
            cobra=cobra,
            liq_edif=liq_edif,
            edificaciones_proyectistas=edificaciones_proyectistas,
            edificaciones_delegados=edificaciones_delegados,
            contactos_orm=contactos_orm,
            valor_proyecto=valor_proyecto,
        )
        return result
