"""
TaludesResultBuilder — construye DTO de resultado para Taludes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Tuple

from modules.liquidaciones.domain.services.builders._entidad_projection_helpers import (
    _proyectar_entidad_desde_proyecto,
)
from modules.liquidaciones.domain.services.builders._calculo_m2_helpers import (
    _build_tarifa_m2_calculo_data,
    _build_liquidacion_m2_calculo_data,
)

if TYPE_CHECKING:
    from modules.liquidaciones.models import (
        LiquidacionGeneral,
        LiquidacionPorMetroCuadrado,
        LiquidacionPorcentajeObra,
    )


class TaludesResultBuilder:
    """
    Builder stateless para construir DTO de resultado de Taludes.

    Los métodos retornan TUPLAS (result, calculo_data) para que el llamador
    (flujo → orchestrator → controller) pueda pasar el cálculo al presenter
    de forma independiente.
    """

    @staticmethod
    def build_result(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        liquidacion_m2: "LiquidacionPorMetroCuadrado",
        subtotal: Decimal,
        igv_valor: Decimal,
    ) -> Tuple:
        """
        Construye un resultado tipado para liquidaciones de Taludes.

        Args:
            liquidacion: LiquidacionGeneral creada.
            proyecto: Instancia de Proyecto (ORM).
            liquidacion_m2: LiquidacionPorMetroCuadrado creada.
            subtotal: Subtotal calculado (= derecho para M2).
            igv_valor: Valor del IGV (ej. 0.18).

        Returns:
            Tuple of (LiquidacionTaludesResult, LiquidacionM2CalculoData)
        """
        from modules.liquidaciones.domain.schemas.taludes import (
            LiquidacionTaludesResult,
        )

        # M2: derecho es el total final — sin IGV
        igv_monto = Decimal("0")
        total = subtotal

        # Construir tarifa data usando helper
        tarifa_m2 = liquidacion_m2.tarifa_aplicada
        tarifa_data = _build_tarifa_m2_calculo_data(tarifa_m2)

        # Construir cálculo M2 data usando helper
        calculo_m2_data = _build_liquidacion_m2_calculo_data(liquidacion_m2, tarifa_data)

        # Proyectar entidad usando helper
        entidad_id, entidad_tipo, entidad_nombre, entidad_ruc = _proyectar_entidad_desde_proyecto(proyecto)

        result = LiquidacionTaludesResult(
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
    def build_result_porcentaje(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        liquidacion_porcentaje: "LiquidacionPorcentajeObra",
        subtotal: Decimal,
        igv_valor: Decimal,
        igv_monto: Decimal,
        total_liquidacion: Decimal,
    ) -> Tuple:
        """
        Construye un resultado tipado para liquidaciones de Taludes
        usando cálculo porcentual (Edificaciones-style).

        Args:
            liquidacion: LiquidacionGeneral creada.
            proyecto: Instancia de Proyecto (ORM).
            liquidacion_porcentaje: LiquidacionPorcentajeObra creada.
            subtotal: Subtotal calculado (= derecho).
            igv_valor: Valor del IGV (ej. 0.18).
            igv_monto: Monto IGV calculado.
            total_liquidacion: Total de la liquidación.

        Returns:
            Tuple of (LiquidacionTaludesResult, LiquidacionPorcentajeObra)
        """
        from modules.liquidaciones.domain.schemas.taludes import (
            LiquidacionTaludesResult,
        )

        # Proyectar entidad usando helper
        entidad_id, entidad_tipo, entidad_nombre, entidad_ruc = _proyectar_entidad_desde_proyecto(proyecto)

        result = LiquidacionTaludesResult(
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
            proyecto_valor_proyecto=Decimal(str(liquidacion_porcentaje.valor_proyecto)),
            municipalidad_id=liquidacion.municipalidad_id,
            municipalidad_nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else "",
            expediente=liquidacion.expediente,
            observacion=liquidacion.observacion,
            igv_valor=Decimal(str(igv_valor)),
            uit_valor=Decimal(str(liquidacion.uit.valor)) if liquidacion.uit else Decimal('0'),
            totales_subtotal=subtotal,
            totales_igv=igv_monto,
            totales_total_liquidacion=total_liquidacion,
            totales_total_a_pagar=total_liquidacion,
        )

        return result, liquidacion_porcentaje
