"""
InspeccionObraFlujo — flujo transaccional para creación de liquidaciones de Inspección de Obra.

Patrón:Replica la estructura de LiquidacionesEdificacionesFlujo.
El flujo es @transaction.atomic y usa sync_to_async para operaciones ORM.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from asgiref.sync import sync_to_async
from injector import inject

from modules.liquidaciones.domain.services.core.inspeccion_obra_core import (
    InspeccionObraCoreService,
)
from modules.liquidaciones.domain.services.core.proyecto_core_service import (
    ProyectoService,
)
from modules.liquidaciones.domain.services.builders.inspeccion_obra_result_builder import (
    InspeccionObraResultBuilder,
)
from modules.liquidaciones.domain.schemas_proyecto import ProyectoInlineData
from modules.liquidaciones.domain.schemas import ProyectistaInlineData
from modules.liquidaciones.domain.constants import TramiteAccion, TipoLiquidacion
from modules.liquidaciones.models import LiquidacionProyectista, LiquidacionInspector
from modules.liquidaciones.domain.services.core.liquidacion_inspector_core import (
    LiquidacionInspectorCore,
    liquidacion_inspector_core,
)
from modules.usuarios.infrastructure.services import ICipClient
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService


class InspeccionObraFlujo:
    """
    Flujo transaccional para crear liquidaciones de Inspección de Obra.

    Coordina: Proyecto (get/upsert) → LiquidacionGeneral →
              LiquidacionInspeccionObra → LiquidacionPorCategoriaVisitas.
    """

    @inject
    def __init__(
        self,
        core: InspeccionObraCoreService,
        proyecto_service: ProyectoService,
        cip_client: ICipClient,
        perfil_ingeniero_core: PerfilIngenieroCoreService,
        inspector_core: LiquidacionInspectorCore = None,
    ):
        self.core = core
        self._proyecto_service = proyecto_service
        self._cip_client = cip_client
        self._perfil_ingeniero_core = perfil_ingeniero_core
        self._inspector_core = inspector_core or liquidacion_inspector_core

    async def _proceso_creacion(
        self,
        liquidacion_previa_id: str,
        proyecto_public_id: Optional[str],
        municipalidad_id: str | None,
        cantidad_visitas: int,
        categoria: str,
        expediente: Optional[str],
        observacion: Optional[str],
        proyecto_inline: Optional[ProyectoInlineData] = None,
        tarifa_id: Optional[str] = None,
        proyectistas_inline: Optional[list[ProyectistaInlineData]] = None,
        inspectores_ids: Optional[list[str]] = None,
    ):
        """
        Proceso de creación de Inspección de Obra basada en liquidación previa.

        Phase 2: Se implementa la derivación de proyecto y municipalidad
        desde la liquidación previa. Los campos deprecated del payload
        (proyecto_inline, proyecto_public_id, municipalidad_id) se ignoran.

        Flujo Phase 2:
        1. Obtener liquidacion_previa por ID y validar que tiene proyecto y municipalidad
        2. Derivar proyecto y municipalidad desde la liquidación previa
        3. Buscar/validar tarifa inspección:
           - Si tarifa_id proporcionado: usar ese ID y validar que corresponde a categoria + tramite_accion
           - Si no: auto-seleccionar por reglas (categoria + tramite_accion)
        4. Si hay proyectistas_inline, validar CIPs (ALL-OR-NOTHING)
        5. Si hay inspectores_ids, validar que son elegibles:
           - Activos, vigentes y con tipo_liquidacion compatible con la previa
        6. En transacción atómica:
           a. Crear LiquidacionGeneral con proyecto/municipalidad derivados
           b. Crear LiquidacionInspeccionObra
           c. Vincular nueva liquidación a la previa via liquidaciones_previas M2M
           d. Upsert proyectistas si hay
           e. Crear LiquidacionPorCategoriaVisitas
           f. Guardar sub_total en LiquidacionGeneral
           g. Asociar inspectores si hay
        7. Construir y retornar resultado tipado
        """
        # Phase 2: Obtener liquidacion_previa y derivar proyecto/municipalidad
        liquidacion_previa = await self._get_liquidacion_previa_model(liquidacion_previa_id)
        if not liquidacion_previa:
            from modules.liquidaciones.domain.exceptions import NotFoundError
            raise NotFoundError(f"Liquidación previa con id={liquidacion_previa_id} no encontrada")

        # Validar que la liquidación previa tiene proyecto y municipalidad
        if not liquidacion_previa.proyecto:
            from modules.liquidaciones.domain.exceptions import NotFoundError
            raise NotFoundError(
                f"La liquidación previa {liquidacion_previa_id} no tiene proyecto asociado. "
                f"No se puede crear una IO sin proyecto."
            )

        if not liquidacion_previa.municipalidad:
            from modules.liquidaciones.domain.exceptions import NotFoundError
            raise NotFoundError(
                f"La liquidación previa {liquidacion_previa_id} no tiene municipalidad asociada. "
                f"No se puede crear una IO sin municipalidad."
            )

        # Derivar proyecto y municipalidad desde la liquidación previa
        proyecto = liquidacion_previa.proyecto
        municipalidad = liquidacion_previa.municipalidad

        # Derivar tipo_liquidacion de la liquidación previa para validar inspectores
        tipo_liquidacion_previa = liquidacion_previa.tipo_liquidacion

        # 3. Buscar/validar tarifa inspección
        try:
            if tarifa_id:
                # Usar la tarifa seleccionada y validarla
                tarifa_visitas = await sync_to_async(self.core._validar_tarifa_inspeccion_por_id)(
                    tarifa_id=tarifa_id,
                    categoria=categoria,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
            else:
                # Auto-selección por reglas
                tarifa_visitas = await sync_to_async(self.core._buscar_tarifa_inspeccion)(
                    categoria=categoria,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
        except ValueError as e:
            from modules.liquidaciones.domain.exceptions import NotFoundError

            raise NotFoundError(str(e))

        # 4. Si hay proyectistas_inline (inline con CIP), validar TODOS los CIPs
        # ALL-OR-NOTHING: si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        if proyectistas_inline:
            await self._validar_proyectistas_inline_cip(proyectistas_inline)

        # 5. Si hay inspectores_ids, validar que son elegibles antes de la transacción
        # ALL-OR-NOTHING: si cualquier inspector no es válido, se rechaza toda la operación
        if inspectores_ids:
            await self._validar_inspectores_inline(inspectores_ids, tipo_liquidacion_previa)

        # Ejecutar bloque transaccional
        def _run_creacion():
            from django.db import transaction

            with transaction.atomic():
                # 5a. Crear LiquidacionGeneral
                liquidacion = self.core._crear_liquidacion_general_nueva(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    tipo_liquidacion="INSPECCION_OBRA",
                    expediente=expediente,
                    observacion=observacion,
                    numero_revision=1,
                )

                # 5b. Crear LiquidacionInspeccionObra
                liq_io = self.core._crear_liquidacion_inspeccion_obra(
                    liquidacion_general=liquidacion,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )

                # 5c. Vincular nueva liquidación a la previa via liquidaciones_previas M2M
                # Esto es trazabilidad, no nueva revisión (numero_revision sigue = 1)
                liquidacion.liquidaciones_previas.add(liquidacion_previa)

                # 5d. Upsert proyectistas si hay inline data
                if proyectistas_inline:
                    proyectistas_ids = self._upsert_proyectistas_inline(
                        proyectistas_inline, municipalidad.id
                    )
                    # Asociar proyectistas a la liquidación vía LiquidacionProyectista
                    for pid in proyectistas_ids:
                        LiquidacionProyectista.objects.create(
                            liquidacion_general=liq_io.liquidacion,
                            proyectista_id=pid,
                        )

                # 5e. Crear LiquidacionPorCategoriaVisitas
                liquidacion_visitas = self.core._crear_calculo_visitas(
                    liquidacion_general=liquidacion,
                    cantidad_visitas=cantidad_visitas,
                    categoria=categoria,
                    tarifa_visitas=tarifa_visitas,
                )

                # 5f. Guardar sub_total (= derecho de visitas, ya calculado y almacenado)
                derecho = liquidacion_visitas.derecho

                liquidacion.sub_total = derecho
                liquidacion.save(update_fields=["sub_total"])

                # 5g. Asociar inspectores si hay
                if inspectores_ids:
                    for inspector_id in inspectores_ids:
                        LiquidacionInspector.objects.create(
                            liquidacion=liquidacion,
                            inspector_id=inspector_id,
                        )

                # 6. Construir resultado
                igv_valor = (
                    Decimal(str(liquidacion.igv.valor))
                    if liquidacion.igv
                    else Decimal("0.18")
                )
                result = InspeccionObraResultBuilder.build_result(
                    liquidacion=liquidacion,
                    proyecto=proyecto,
                    liquidacion_visitas=liquidacion_visitas,
                    subtotal=derecho,
                    igv_valor=igv_valor,
                )
                return result

        return await sync_to_async(_run_creacion, thread_sensitive=True)()

    async def _get_municipalidad_model(self, municipalidad_id: str):
        """Obtiene modelo Municipalidad por ID."""
        from modules.entidades.models import Municipalidad

        return await sync_to_async(
            lambda: (
                Municipalidad.objects.filter(id=municipalidad_id)
                .select_related("provincia", "distrito")
                .first()
            )
        )()

    async def _get_liquidacion_previa_model(self, liquidacion_previa_id: str):
        """
        Obtiene el modelo LiquidacionGeneral (liquidación previa) por ID.

        Phase 2: Se usa para derivar proyecto y municipalidad de la IO.

        Args:
            liquidacion_previa_id: UUID de la liquidación previa.

        Returns:
            LiquidacionGeneral o None si no existe.
        """
        from modules.liquidaciones.models import LiquidacionGeneral

        return await sync_to_async(
            lambda: (
                LiquidacionGeneral.objects.filter(id=liquidacion_previa_id)
                .select_related("proyecto", "proyecto__entidad", "municipalidad")
                .first()
            )
        )()

    async def _validar_proyectistas_inline_cip(self, proyectistas_inline: list[ProyectistaInlineData]):
        """
        Valida TODOS los CIPs de los proyectistas inline antes de crear la liquidación.

        ALL-OR-NOTHING: Si cualquier CIP falla o no está habilitado, se rechaza toda la operación.
        """
        from core.exceptions import CipNotFoundError, CipServiceUnavailableError
        from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData

        for p in proyectistas_inline:
            cip = p.cip
            if not cip:
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(f"CIP es requerido para cada proyectista")

            # Normalizar CIP
            normalized_cip = self._perfil_ingeniero_core._normalizar_cip(cip)
            if not normalized_cip:
                from modules.liquidaciones.domain.exceptions import BusinessError
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
                from modules.liquidaciones.domain.exceptions import BusinessError
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
                from modules.liquidaciones.domain.exceptions import NotFoundError
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

    async def _validar_inspectores_inline(
        self,
        inspectores_ids: list[str],
        tipo_liquidacion_previa: str,
    ):
        """
        Valida que todos los inspectores_ids sean elegibles para la IO.

        ALL-OR-NOTHING: si cualquier inspector no es válido, se rechaza toda la operación.

        Validaciones por inspector:
        1. Existe y está activo (status=ACTIVO)
        2. Está vigente (vigencia >= hoy)
        3. Su tipo_liquidacion es compatible con la liquidacion previa (EDIFICACION o HABILITACION_URBANA)

        Args:
            inspectores_ids: Lista de UUIDs de inspectores a validar.
            tipo_liquidacion_previa: Tipo de la liquidación previa (EDIFICACION o HABILITACION_URBANA).

        Raises:
            BusinessError: Si algún inspector no es válido.
        """
        import uuid

        for inspector_id_str in inspectores_ids:
            inspector_id = uuid.UUID(inspector_id_str)

            # 1. Verificar que el inspector existe
            inspector = await sync_to_async(self._inspector_core._obtener_inspector_por_id)(inspector_id)
            if not inspector:
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(
                    f"El inspector con ID '{inspector_id_str}' no fue encontrado."
                )

            # 2. Verificar que está activo
            if not await sync_to_async(self._inspector_core._es_inspector_activo)(inspector_id):
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(
                    f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' no está activo."
                )

            # 3. Verificar que está vigente
            if not await sync_to_async(self._inspector_core._inspector_vigente)(inspector_id):
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(
                    f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' no está vigente."
                )

            # 4. Verificar compatibilidad de tipo
            if not await sync_to_async(self._inspector_core._tipo_inspector_compatible)(
                inspector_id, tipo_liquidacion_previa
            ):
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(
                    f"El inspector '{inspector.perfil_ingeniero.nombre_completo}' "
                    f"no corresponde al tipo '{tipo_liquidacion_previa}' de la liquidación previa."
                )

    async def _proceso_cotizar_primera_revision(
        self,
        cantidad_visitas: int,
        categoria: str,
        tarifa_id: str | None = None,
    ):
        """
        Cotiza primera revisión de Inspección de Obra sin guardar en BD.

        1. Obtener IGV/UIT vigentes
        2. Buscar/validar tarifa inspección:
           - Si tarifa_id proporcionado: usar ese ID y validar que corresponde a categoria
           - Si no: auto-seleccionar por reglas (categoria + tramite_accion)
        3. Calcular usando helpers (sin persistencia)
        4. Retornar resultado de cotización

        No crea ningún registro en BD.

        Args:
            cantidad_visitas: Cantidad de visitas de inspección.
            categoria: Categoría de inspección (A, B, C, etc.).
            tarifa_id: ID de la tarifa específica a usar (opcional).

        Returns:
            CotizacionVisitasQuoteData
        """
        from decimal import Decimal

        from modules.liquidaciones.domain.schemas.shared import (
            CotizacionVisitasQuoteData,
            CotizacionVisitasRevisionData,
            CotizacionTotalesData,
            CotizacionMetadataData,
            TarifaVisitasCalculoData,
        )
        from modules.liquidaciones.domain.services.core.calculos_helpers import (
            _calcular_monto_visitas,
        )

        # 1. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()
        igv_valor, uit_valor = variables

        # 2. Buscar/validar tarifa inspección
        try:
            if tarifa_id:
                tarifa_visitas = await sync_to_async(self.core._validar_tarifa_inspeccion_por_id)(
                    tarifa_id=tarifa_id,
                    categoria=categoria,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
            else:
                tarifa_visitas = await sync_to_async(self.core._buscar_tarifa_inspeccion)(
                    categoria=categoria,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
        except ValueError as e:
            from modules.liquidaciones.domain.exceptions import NotFoundError
            raise NotFoundError(str(e))

        # 3. Calcular (sin persistencia)
        visitas_base_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=tarifa_visitas.costo_por_visita,
            visitas_minimas=tarifa_visitas.visitas_minimas,
        )

        # Calcular totales
        subtotal = derecho
        igv_monto = subtotal * igv_valor
        total_liquidacion = subtotal + igv_monto

        # 4. Retornar resultado de cotización
        return CotizacionVisitasQuoteData(
            numero_revision=1,
            calculo_visitas=CotizacionVisitasRevisionData(
                cantidad_visitas=cantidad_visitas,
                visitas_base_calculo=visitas_base_calculo,
                derecho=derecho,
                categoria=categoria,
                tarifa=TarifaVisitasCalculoData(
                    id=tarifa_visitas.id,
                    costo_por_visita=tarifa_visitas.costo_por_visita,
                    visitas_minimas=tarifa_visitas.visitas_minimas,
                ),
            ),
            totales=CotizacionTotalesData(
                subtotal=subtotal,
                igv=igv_monto,
                total=total_liquidacion,
                liquidacion_total=total_liquidacion,
                total_a_pagar=total_liquidacion,
            ),
            metadata=CotizacionMetadataData(
                igv_valor=igv_valor,
                uit_valor=uit_valor,
                cantidad_visitas=cantidad_visitas,
            ),
        )

    async def _proceso_buscar_previas_por_documento(
        self,
        numero_documento: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """
        Busca liquidaciones previas de Inspección de Obra por número de documento de entidad.

        Las liquidaciones previas candidatas son aquellas con:
        - tipo_liquidacion = "INSPECCION_OBRA"
        - numero_revision = 0 (registros preliminares)

        Args:
            numero_documento: DNI o RUC de la entidad asociada al proyecto.
            page: Número de página (1-indexed).
            page_size: Elementos por página.

        Returns:
            (lista_de_datos_materializados, total)
        """
        return await sync_to_async(
            self.core._buscar_liquidaciones_previas_por_documento
        )(
            numero_documento=numero_documento,
            page=page,
            page_size=page_size,
        )
