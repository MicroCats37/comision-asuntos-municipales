"""
Liquidaciones Nuevas Result Builder — construye DTOs de resultado para los 5 nuevos formularios.

Este módulo contiene la lógica de construcción de resultados (Results) que antes vivía
en el flujo. El flujo delega la construcción de DTOs a este builder, manteniendo su
responsabilidad en la coordinación de pasos del caso de uso (validación,
transacciones, llamadas core).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union, Tuple

if TYPE_CHECKING:
    from modules.liquidaciones.models import (
        LiquidacionGeneral,
        LiquidacionPorMetroCuadrado,
        LiquidacionPorCategoriaVisitas,
    )


class LiquidacionesNuevasResultBuilder:
    """
    Builder stateless para construir DTOs de resultado de liquidaciones nuevas.

    Agrupa métodos de construcción de estructuras anidadas tipadas que antes
    vivían en el flujo. Al estar separados, el flujo solo coordina pasos de
    negocio y delega la construcción de DTOs a este builder.

    Los métodos retornan TUPLAS (result, calculo_data) para que el llamador
    (flujo → orchestrator → controller) pueda pasar el cálculo al presenter
    de forma independiente.
    """

    @staticmethod
    def build_result_m2(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        liquidacion_m2: "LiquidacionPorMetroCuadrado",
        subtotal: Decimal,
        igv_valor: Decimal,
    ) -> Tuple:
        """
        Construye un resultado tipado para liquidaciones M2 (HU, MS, IV, TAL).

        Args:
            liquidacion: LiquidacionGeneral creada.
            proyecto: Instancia de Proyecto (ORM).
            liquidacion_m2: LiquidacionPorMetroCuadrado creada.
            subtotal: Subtotal calculado (= derecho para M2).
            igv_valor: Valor del IGV (ej. 0.18).

        Returns:
            Tuple of (LiquidacionXxxResult, LiquidacionM2CalculoData)
        """
        from modules.liquidaciones.domain.schemas_nuevos import (
            LiquidacionHabilitacionUrbanaResult,
            LiquidacionMecanicaSuelosResult,
            LiquidacionImpactoVialResult,
            LiquidacionTaludesResult,
            TarifaM2CalculoData,
            LiquidacionM2CalculoData,
        )
        from modules.liquidaciones.domain.constants import TipoLiquidacion

        tipo = liquidacion.tipo_liquidacion
        igv_monto = subtotal * igv_valor
        total = subtotal + igv_monto

        # Construir tarifa data
        tarifa_m2 = liquidacion_m2.tarifa_aplicada
        tarifa_data = TarifaM2CalculoData(
            id=tarifa_m2.id,
            costo_por_m2=tarifa_m2.costo_por_m2,
            area_minima=tarifa_m2.area_minima,
            derecho_minimo=tarifa_m2.derecho_minimo,
            derecho_maximo=tarifa_m2.derecho_maximo,
        )

        # Construir cálculo M2 data usando el derecho almacenado en el modelo
        calculo_m2_data = LiquidacionM2CalculoData(
            area_solicitada=liquidacion_m2.area_solicitada,
            area_base_calculo=liquidacion_m2.area_base_calculo,
            derecho=liquidacion_m2.derecho,
            tarifa=tarifa_data,
        )

        # Proyectar entidad
        entidad_id = getattr(proyecto, 'entidad_id', None)
        entidad_tipo = getattr(proyecto, 'entidad_tipo_documento', None)
        entidad_nombre = getattr(proyecto, 'entidad_razon_social', None)
        entidad_ruc = getattr(proyecto, 'entidad_numero_documento', None) if entidad_tipo == 'RUC' else None

        # Seleccionar tipo de resultado según tipo_liquidacion
        if tipo == TipoLiquidacion.HABILITACION_URBANA:
            result_class = LiquidacionHabilitacionUrbanaResult
        elif tipo == TipoLiquidacion.MECANICA_SUELOS:
            result_class = LiquidacionMecanicaSuelosResult
        elif tipo == TipoLiquidacion.IMPACTO_VIAL:
            result_class = LiquidacionImpactoVialResult
        elif tipo == TipoLiquidacion.TALUDES:
            result_class = LiquidacionTaludesResult
        else:
            raise ValueError(f"TipoLiquidacion {tipo} no soportado para build_result_m2")

        result = result_class(
            liquidacion_id=liquidacion.id,
            liquidacion_public_id=liquidacion.public_id,
            numero_revision=liquidacion.numero_revision,
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else "",
            proyecto_id=proyecto.id,
            proyecto_public_id=proyecto.public_id or "",
            proyecto_nombre=proyecto.denominacion,
            proyecto_direccion=getattr(proyecto, 'direccion', None),
            proyecto_entidad_id=entidad_id,
            proyecto_entidad_tipo=entidad_tipo,
            proyecto_entidad_nombre=entidad_nombre,
            proyecto_entidad_ruc=entidad_ruc,
            municipalidad_id=liquidacion.municipalidad_id,
            municipalidad_nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else "",
            expediente=liquidacion.expediente,
            observacion=liquidacion.observacion,
            igv_valor=Decimal(str(igv_valor)),
            uit_valor=Decimal(str(liquidacion.uit.valor)) if liquidacion.uit else Decimal('0'),
            totales_subtotal=subtotal,
            totales_igv=igv_monto,
            totales_total_liquidacion=total,
            totales_total_a_pagar=total,
        )

        return result, calculo_m2_data

    @staticmethod
    def build_result_visitas(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        liquidacion_visitas: "LiquidacionPorCategoriaVisitas",
        subtotal: Decimal,
        igv_valor: Decimal,
    ) -> Tuple:
        """
        Construye un resultado tipado para liquidaciones de Inspección de Obra.

        Args:
            liquidacion: LiquidacionGeneral creada.
            proyecto: Instancia de Proyecto (ORM).
            liquidacion_visitas: LiquidacionPorCategoriaVisitas creada.
            subtotal: Subtotal calculado (= derecho para visitas).
            igv_valor: Valor del IGV (ej. 0.18).

        Returns:
            Tuple of (LiquidacionInspeccionObraResult, LiquidacionVisitasCalculoData)
        """
        from modules.liquidaciones.domain.schemas_nuevos import (
            LiquidacionInspeccionObraResult,
            TarifaVisitasCalculoData,
            LiquidacionVisitasCalculoData,
        )

        igv_monto = subtotal * igv_valor
        total = subtotal + igv_monto

        # Construir tarifa data
        tarifa_visitas = liquidacion_visitas.tarifa_aplicada
        tarifa_data = TarifaVisitasCalculoData(
            id=tarifa_visitas.id,
            costo_por_visita=tarifa_visitas.costo_por_visita,
            visitas_minimas=tarifa_visitas.visitas_minimas,
        )

        # Construir cálculo visitas data usando los valores almacenados en el modelo
        calculo_visitas_data = LiquidacionVisitasCalculoData(
            cantidad_visitas=liquidacion_visitas.cantidad_visitas,
            visitas_base_calculo=liquidacion_visitas.visitas_base_calculo,
            derecho=liquidacion_visitas.derecho,
            categoria=liquidacion_visitas.categoria,
            tarifa=tarifa_data,
        )

        # Proyectar entidad
        entidad_id = getattr(proyecto, 'entidad_id', None)
        entidad_tipo = getattr(proyecto, 'entidad_tipo_documento', None)
        entidad_nombre = getattr(proyecto, 'entidad_razon_social', None)
        entidad_ruc = getattr(proyecto, 'entidad_numero_documento', None) if entidad_tipo == 'RUC' else None

        result = LiquidacionInspeccionObraResult(
            liquidacion_id=liquidacion.id,
            liquidacion_public_id=liquidacion.public_id,
            numero_revision=liquidacion.numero_revision,
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else "",
            proyecto_id=proyecto.id,
            proyecto_public_id=proyecto.public_id or "",
            proyecto_nombre=proyecto.denominacion,
            proyecto_direccion=getattr(proyecto, 'direccion', None),
            proyecto_entidad_id=entidad_id,
            proyecto_entidad_tipo=entidad_tipo,
            proyecto_entidad_nombre=entidad_nombre,
            proyecto_entidad_ruc=entidad_ruc,
            municipalidad_id=liquidacion.municipalidad_id,
            municipalidad_nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else "",
            expediente=liquidacion.expediente,
            observacion=liquidacion.observacion,
            igv_valor=Decimal(str(igv_valor)),
            uit_valor=Decimal(str(liquidacion.uit.valor)) if liquidacion.uit else Decimal('0'),
            totales_subtotal=subtotal,
            totales_igv=igv_monto,
            totales_total_liquidacion=total,
            totales_total_a_pagar=total,
        )

        return result, calculo_visitas_data
