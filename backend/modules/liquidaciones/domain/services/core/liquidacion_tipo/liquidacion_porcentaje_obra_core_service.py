"""
Core service for PorcentajeObra (Edificaciones) calculations.

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
    ) -> List[TarifaPorcentajeObra]:
        """
        Hybrid resolution: empty list → auto-fill, non-empty → validate each.
        
        Returns the list of TarifaPorcentajeObra to apply.
        Caller (Orchestrator) is responsible for raising HttpError on invalid tarifas.
        """
        if not payload_tarifas_ids:
            # Auto-fill mode: get all vigentes for EDIFICACION
            bases = TarifaLiquidacionBase.objects.vigentes().filter(
                tipo_liquidacion=TipoLiquidacion.EDIFICACION
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
    
    def get_tarifas_porcentaje_vigentes(self) -> List[TarifaPorcentajeObra]:
        """Returns all vigentes TarifaPorcentajeObra for EDIFICACION."""
        bases = TarifaLiquidacionBase.objects.vigentes().filter(
            tipo_liquidacion=TipoLiquidacion.EDIFICACION
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
    ) -> CotizacionPorcentajeObraData:
        """
        Pure arithmetic for the PorcentajeObra motor.
        
        Steps:
        1. Per-detalle: subtotal = valor × tarifa.porcentaje
        2. Sum all subtotals
        3. Apply clamping at TOTAL (distributed proportionally)
        4. Calculate IGV per detalle
        5. Calculate UIT per detalle (informational)
        """
        if not tarifas:
            raise ValueError("At least one tarifa is required")
        
        # Step 1: per-detalle calculation (RAW, no clamping yet)
        detalles_raw: List[DetallePorcentajeObraData] = []
        for tarifa in tarifas:
            subtotal = valor_declarado * tarifa.porcentaje_liquidacion
            detalles_raw.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=TarifaPorcentajeObraAplicada(
                        tarifa_id=str(tarifa.id),
                        porcentaje_liquidacion=tarifa.porcentaje_liquidacion,
                        especialidad_id=str(tarifa.especialidad.id),
                        especialidad_nombre=tarifa.especialidad.nombre,
                    ),
                    porcentaje_aplicado=tarifa.porcentaje_liquidacion,
                    subtotal=subtotal,
                    igv=subtotal * igv_porcentaje,
                    uit=valor_declarado * derecho.porcentaje_minimo_uit,
                    total=subtotal + (subtotal * igv_porcentaje),
                )
            )
        
        # Step 2: aggregate
        porcentaje_liquidacion = sum(
            (t.porcentaje_liquidacion for t in tarifas), Decimal("0")
        )
        total_calculado = sum((d.subtotal for d in detalles_raw), Decimal("0"))
        
        # Step 3: clamping at TOTAL
        detalles_finales = detalles_raw
        if total_calculado < derecho.derecho_minimo:
            factor = derecho.derecho_minimo / total_calculado
            detalles_finales = self._distribute_clamp(
                detalles_raw, factor, igv_porcentaje, valor_declarado, derecho
            )
        elif derecho.derecho_maximo is not None and total_calculado > derecho.derecho_maximo:
            factor = derecho.derecho_maximo / total_calculado
            detalles_finales = self._distribute_clamp(
                detalles_raw, factor, igv_porcentaje, valor_declarado, derecho
            )
        
        total_subtotal = sum((d.subtotal for d in detalles_finales), Decimal("0"))
        total = sum((d.total for d in detalles_finales), Decimal("0"))
        
        return CotizacionPorcentajeObraData(
            valor_declarado=valor_declarado,
            porcentaje_liquidacion=porcentaje_liquidacion,
            tipo_tramite=None,  # FUTURE: activate
            derecho_minimo=derecho.derecho_minimo,
            derecho_maximo=derecho.derecho_maximo,
            porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=str(derecho.id),
            detalles=detalles_finales,
            total_subtotal=total_subtotal,
            total=total,
        )
    
    def _distribute_clamp(
        self,
        detalles_raw: List[DetallePorcentajeObraData],
        factor: Decimal,
        igv_porcentaje: Decimal,
        valor_declarado: Decimal,
        derecho: DerechoPorcentajeObra,
    ) -> List[DetallePorcentajeObraData]:
        """Distribute clamped total proportionally across detalles."""
        result = []
        for d in detalles_raw:
            new_subtotal = d.subtotal * factor
            new_igv = new_subtotal * igv_porcentaje
            result.append(
                DetallePorcentajeObraData(
                    tarifa_aplicada=d.tarifa_aplicada,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=new_subtotal,
                    igv=new_igv,
                    uit=valor_declarado * derecho.porcentaje_minimo_uit,
                    total=new_subtotal + new_igv,
                )
            )
        return result
    
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
            derecho_minimo=derecho.derecho_minimo,
            derecho_maximo=derecho.derecho_maximo,
            porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
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
