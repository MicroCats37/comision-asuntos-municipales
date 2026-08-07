"""
LiquidacionPorMetroCuadradoFlujo — transactional flow for M2 liquidacion creation.

Uses @transaction.atomic() to ensure atomic creation of all related entities.
Reutilizable por cualquier especialidad basada en Metro Cuadrado.
"""
from decimal import Decimal
from django.db import transaction
from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)


class LiquidacionPorMetroCuadradoFlujo:
    """
    Transactional flow for creating any M2-based liquidacion.
    Consumes general core + M2 core.
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        m2_core: LiquidacionPorMetroCuadradoCoreService,
    ):
        self.general_core = general_core
        self.m2_core = m2_core

    @transaction.atomic()
    def crear_liquidacion_m2_transaccional(
        self,
        usuario_id: int,
        tipo_liquidacion: str,
        municipalidad_id: str,
        expediente: str,
        observacion: str | None,
        proyecto_data: dict,
        area_solicitada: float,
        tarifa_m2_id: str,
    ) -> tuple[LiquidacionGeneral, LiquidacionPorMetroCuadrado]:
        """
        Flujo atómico y genérico para crear cualquier liquidación por Metro Cuadrado.
        """
        # 1. Obtener entidad si existe
        entidad = None
        numero_documento = proyecto_data.get("entidad_numero_documento")
        if numero_documento:
            entidad = self.general_core.create_entidad(
                tipo_documento=proyecto_data.get("entidad_tipo_documento", "RUC"),
                numero_documento=numero_documento,
                razon_social=proyecto_data.get("entidad_razon_social"),
            )

        # 2. Crear proyecto
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # 3. Calcular montos inyectando vigencia
        calculo = self.m2_core.calcular_cotizacion_m2(
            tipo_liquidacion=tipo_liquidacion,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
        )

        # 4. Crear LiquidacionGeneral (con valores calculados)
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=1,
        )
        liquidacion_general.sub_total = Decimal(str(calculo.subtotal))
        liquidacion_general.total = Decimal(str(calculo.total))
        liquidacion_general.usuario_creador_id = usuario_id

        tarifa = self.m2_core.get_tarifa_m2_vigente(tipo_liquidacion)
        derecho = self.m2_core.get_derecho_minimo_m2_vigente()

        liquidacion_general.save()

        # 5. Crear la liquidación específica de cálculo M2
        liquidacion_m2 = self.m2_core.create_liquidacion_por_metro_cuadrado(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            tarifa_aplicada=tarifa,
            derecho_aplicado=derecho,
            subtotal=liquidacion_general.sub_total,
            total=liquidacion_general.total,
        )

        return liquidacion_general, liquidacion_m2
