"""
InspeccionObraResultBuilder — construye DTO de resultado para Inspección de Obra.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Tuple

from modules.liquidaciones.domain.services.builders._entidad_projection_helpers import (
    _proyectar_entidad_desde_proyecto,
)
from modules.liquidaciones.domain.services.builders._calculo_visitas_helpers import (
    _build_tarifa_visitas_calculo_data,
    _build_liquidacion_visitas_calculo_data,
)

if TYPE_CHECKING:
    from modules.liquidaciones.models import (
        LiquidacionGeneral,
        LiquidacionPorCategoriaVisitas,
    )


class InspeccionObraResultBuilder:
    """
    Builder stateless para construir DTO de resultado de Inspección de Obra.

    Los métodos retornan TUPLAS (result, calculo_data) para que el llamador
    (flujo → orchestrator → controller) pueda pasar el cálculo al presenter
    de forma independiente.
    """

    @staticmethod
    def build_result(
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
        from modules.liquidaciones.domain.schemas.inspeccion_obra import (
            LiquidacionInspeccionObraResult,
        )

        igv_monto = subtotal * igv_valor
        total = subtotal + igv_monto

        # Construir tarifa data usando helper
        tarifa_visitas = liquidacion_visitas.tarifa_aplicada
        tarifa_data = _build_tarifa_visitas_calculo_data(tarifa_visitas)

        # Construir cálculo visitas data usando helper
        calculo_visitas_data = _build_liquidacion_visitas_calculo_data(liquidacion_visitas, tarifa_data)

        # Proyectar entidad usando helper
        entidad_id, entidad_tipo, entidad_nombre, entidad_ruc = _proyectar_entidad_desde_proyecto(proyecto)

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
            municipalidad_codigo=liquidacion.municipalidad.codigo if liquidacion.municipalidad else None,
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
