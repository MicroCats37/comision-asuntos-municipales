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
from modules.liquidaciones.domain.constants import TramiteAccion


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
    ):
        self.core = core
        self._proyecto_service = proyecto_service

    async def _proceso_creacion(
        self,
        proyecto_public_id: Optional[str],
        municipalidad_id: str,
        cantidad_visitas: int,
        categoria: str,
        expediente: Optional[str],
        observacion: Optional[str],
        proyecto_inline: Optional[ProyectoInlineData] = None,
        tarifa_id: Optional[str] = None,
    ):
        """
        Proceso de creación de primera revisión de Inspección de Obra.

        1. Obtener o crear proyecto (inline o por public_id)
        2. Buscar municipalidad por ID
        3. Buscar/validar tarifa inspección:
           - Si tarifa_id proporcionado: usar ese ID y validar que corresponde a categoria + tramite_accion
           - Si no: auto-seleccionar por reglas (categoria + tramite_accion)
        4. En transacción atómica:
           a. Crear LiquidacionGeneral
           b. Crear LiquidacionInspeccionObra
           c. Crear LiquidacionPorCategoriaVisitas
           d. Guardar sub_total en LiquidacionGeneral
        5. Construir y retornar resultado tipado
        """
        # 1. Obtener o crear proyecto
        if proyecto_inline:
            proyecto = await sync_to_async(
                self._proyecto_service._crear_proyecto_inline
            )(proyecto_inline)
        else:
            proyecto = await sync_to_async(
                self._proyecto_service._buscar_por_public_id
            )(proyecto_public_id)
            if not proyecto:
                from modules.liquidaciones.domain.exceptions import (
                    ProyectoNotFoundError,
                )
                raise ProyectoNotFoundError(
                    f"Proyecto con public_id={proyecto_public_id} no encontrado"
                )

        # 2. Buscar municipalidad
        municipalidad = await self._get_municipalidad_model(municipalidad_id)
        if not municipalidad:
            from modules.liquidaciones.domain.exceptions import NotFoundError

            raise NotFoundError(f"Municipalidad con id={municipalidad_id}")

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

        # Ejecutar bloque transaccional
        def _run_creacion():
            from django.db import transaction

            with transaction.atomic():
                # 4a. Crear LiquidacionGeneral
                liquidacion = self.core._crear_liquidacion_general_nueva(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    tipo_liquidacion="INSPECCION_OBRA",
                    expediente=expediente,
                    observacion=observacion,
                    numero_revision=1,
                )

                # 4b. Crear LiquidacionInspeccionObra
                self.core._crear_liquidacion_inspeccion_obra(
                    liquidacion_general=liquidacion,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )

                # 4c. Crear LiquidacionPorCategoriaVisitas
                liquidacion_visitas = self.core._crear_calculo_visitas(
                    liquidacion_general=liquidacion,
                    cantidad_visitas=cantidad_visitas,
                    categoria=categoria,
                    tarifa_visitas=tarifa_visitas,
                )

                # 4d. Guardar sub_total (= derecho de visitas, ya calculado y almacenado)
                derecho = liquidacion_visitas.derecho

                liquidacion.sub_total = derecho
                liquidacion.save(update_fields=["sub_total"])

                # 5. Construir resultado
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
