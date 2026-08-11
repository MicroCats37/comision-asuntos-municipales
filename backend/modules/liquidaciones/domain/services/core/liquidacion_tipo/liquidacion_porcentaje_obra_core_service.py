"""
Core service for PorcentajeObra (PorcentajeObra) calculations.

Pure ORM + arithmetic. No HttpError, no @transaction.atomic, no business rules.
"""
from decimal import Decimal
from typing import List, Optional
from modules.liquidaciones.domain.constants import TipoLiquidacion

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorcentajeObra,
    TarifaLiquidacionBase,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    DatosPorcentajeObra,
    TarifaPorcentajeObraAplicada,
    LiquidacionPorcentajeObraData,
    DetallePorcentajeObraData,
    CotizacionPorcentajeObraData,
)


class LiquidacionPorcentajeObraCoreService:
    """Service for PorcentajeObra motor calculations and ORM operations."""
    
    def resolver_tarifas(
        self,
        payload_tarifas_ids: List[str],
        tipo_liquidacion: str,
    ) -> List[TarifaPorcentajeObra]:
        """
        Hybrid resolution: empty list → auto-fill, non-empty → validate each.
        
        Returns the list of TarifaPorcentajeObra to apply.
        Caller (Orchestrator) is responsible for raising HttpError on invalid tarifas.
        
        Args:
            payload_tarifas_ids: List of tariff IDs to validate, or empty for auto-fill.
            tipo_liquidacion: The liquidacion type (e.g., TipoLiquidacion.EDIFICACION).
        """
        if not payload_tarifas_ids:
            # Auto-fill mode: get all vigentes for the specified tipo_liquidacion
            bases = TarifaLiquidacionBase.objects.vigentes().filter(
                tipo_liquidacion__codigo=tipo_liquidacion
            )
            return list(
                TarifaPorcentajeObra.objects.filter(
                    tarifa_base__in=bases
                ).select_related("tarifa_base", "especialidad")
            )
        else:
            # Explicit mode: fetch and return for validation
            return list(
                TarifaPorcentajeObra.objects.filter(
                    id__in=payload_tarifas_ids
                ).select_related("tarifa_base", "especialidad")
            )
    
    def get_derecho_porcentaje_vigente(self) -> DerechoPorcentajeObra:
        """Returns the current vigente DerechoPorcentajeObra."""
        return DerechoPorcentajeObra.objects.vigentes().first()
    
    def get_tarifas_porcentaje_vigentes(self, tipo_liquidacion: str) -> List[TarifaPorcentajeObra]:
        """
        Returns all vigentes TarifaPorcentajeObra for the specified tipo_liquidacion.
        
        Args:
            tipo_liquidacion: The liquidacion type (e.g., TipoLiquidacion.EDIFICACION).
        """
        bases = TarifaLiquidacionBase.objects.vigentes().filter(
            tipo_liquidacion__codigo=tipo_liquidacion
        )
        return list(
            TarifaPorcentajeObra.objects.filter(
                tarifa_base__in=bases
            ).select_related("tarifa_base", "especialidad")
        )
    
    def calcular_cotizacion_po(
        self,
        valor_declarado: Decimal,
        tarifas: List[TarifaPorcentajeObra],
        igv_porcentaje: Decimal,
        derecho: DerechoPorcentajeObra,
        uit_valor: Decimal,
    ) -> CotizacionPorcentajeObraData:
        """
        Pure arithmetic for the PorcentajeObra motor.

        Steps:
        1. Sumar porcentajes de todas las tarifas (ej: 3 x 0.05% = 0.15%)
        2. subtotal_bruto = valor_declarado x porcentaje_total
        3. minimo = uit_valor x derecho.porcentaje_minimo_uit (aplica a la LIQUIDACION, no por tarifa)
        4. subtotal_total = max(subtotal_bruto, minimo)
        5. clamp a derecho_maximo si aplica
        6. Repartir subtotal_total proporcionalmente entre detalles
        7. igv = subtotal_total x igv_porcentaje
        8. total = subtotal_total + igv
        """
        if not tarifas:
            raise ValueError("At least one tarifa is required")

        # Paso 1-2: subtotal bruto agregado (NO por tarifa)
        porcentaje_total = sum(
            (t.porcentaje_liquidacion for t in tarifas), Decimal("0")
        )
        subtotal_bruto = valor_declarado * porcentaje_total

        # Paso 3-4: minimo aplica a la liquidacion completa (UNA vez)
        minimo = uit_valor * derecho.porcentaje_minimo_uit
        subtotal_total = max(subtotal_bruto, minimo)

        # Paso 5: clamp a maximo si aplica
        if derecho.derecho_maximo is not None and subtotal_total > derecho.derecho_maximo:
            subtotal_total = derecho.derecho_maximo

        # Paso 6: repartir proporcionalmente entre detalles
        detalles: List[DetallePorcentajeObraData] = []
        for tarifa in tarifas:
            # Proporcion de esta tarifa sobre el total
            if porcentaje_total > 0:
                proporcion = tarifa.porcentaje_liquidacion / porcentaje_total
            else:
                proporcion = Decimal("1") / Decimal(len(tarifas))

            subtotal_detalle = subtotal_total * proporcion
            igv_detalle = subtotal_detalle * igv_porcentaje

            detalles.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=TarifaPorcentajeObraAplicada(
                        tarifa_id=str(tarifa.id),
                        porcentaje_liquidacion=tarifa.porcentaje_liquidacion,
                        especialidad_id=str(tarifa.especialidad.id),
                        especialidad_nombre=tarifa.especialidad.nombre,
                    ),
                    porcentaje_aplicado=tarifa.porcentaje_liquidacion,
                    subtotal=subtotal_detalle,
                    igv=igv_detalle,
                    uit=minimo,
                    total=subtotal_detalle + igv_detalle,
                )
            )

        # Paso 7-8: agregados
        porcentaje_liquidacion = porcentaje_total
        total_subtotal = sum((d.subtotal for d in detalles), Decimal("0"))
        total = sum((d.total for d in detalles), Decimal("0"))

        # Derecho mínimo: si la tarifa no trae valor absoluto, se calcula
        # como (UIT * porcentaje_minimo_uit) + IGV vigente, sin hardcodear.
        derecho_minimo_calculado = (
            uit_valor * derecho.porcentaje_minimo_uit * (Decimal("1") + igv_porcentaje)
        )

        return CotizacionPorcentajeObraData(
            valor_declarado=valor_declarado,
            porcentaje_liquidacion=porcentaje_liquidacion,
            tipo_tramite=None,  # FUTURE: activate
            derecho_minimo=derecho.derecho_minimo or derecho_minimo_calculado,
            derecho_maximo=derecho.derecho_maximo,
            porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=str(derecho.id),
            detalles=detalles,
            total_subtotal=total_subtotal,
            total=total,
        )
    
    
    def create_liquidacion_porcentaje_obra(
        self,
        liquidacion_general,
        cotizacion: CotizacionPorcentajeObraData,
        derecho: DerechoPorcentajeObra,
        # FUTURE: tipo_tramite: Optional[str] = None,
    ) -> LiquidacionPorcentajeObra:
        """Creates LiquidacionPorcentajeObra + all Detalles in DB."""
        liquidacion_po = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion_general,
            tipo_tramite=None,  # FUTURE: activate when frontend sends it
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado=derecho,
        )
        # Create detalles
        for detalle in cotizacion.detalles:
            tarifa = TarifaPorcentajeObra.objects.get(
                id=detalle.tarifa_aplicada.tarifa_id
            )
            LiquidacionPorcentajeObraDetalle.objects.create(
                liquidacion_porcentaje=liquidacion_po,
                tarifa_aplicada=tarifa,
                especialidad=tarifa.especialidad,
                porcentaje_aplicado=detalle.porcentaje_aplicado,
                subtotal=detalle.subtotal,
                igv=detalle.igv,
                uit=detalle.uit,
                total=detalle.total,
            )
        return liquidacion_po
