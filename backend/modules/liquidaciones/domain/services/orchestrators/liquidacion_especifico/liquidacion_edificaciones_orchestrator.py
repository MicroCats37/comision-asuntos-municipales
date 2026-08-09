"""
Orchestrator for Edificaciones (PorcentajeObra) first revision.

Validates input, applies clamping at TOTAL with proportional distribution,
maps Presentation Schema -> Domain DTO.

Architecture: Orchestrator owns business rules (clamping). No @transaction.atomic.
"""
from decimal import Decimal
from typing import List
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_edificaciones_flujo import (
    LiquidacionEdificacionesFlujo,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    DatosPorcentajeObra,
    LiquidacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.edificaciones_primera_revision_data import (
    EdificacionesPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.edificaciones_primera_revision_result import (
    EdificacionesPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
    CotizacionPorcentajeObraDetalleResult,
)


class LiquidacionEdificacionesOrchestrator:
    """
    Orchestrator for Edificaciones (PorcentajeObra).
    
    Mirrors the MecanicaSuelos pattern but:
    - Uses PorcentajeObra Core service (not M2)
    - Handles hybrid resolution (auto-fill vs explicit tarifas)
    - tipo_tramite stays NULL for now (FUTURE comment)
    """
    
    def _validar_tarifa_explicita(self, tarifa) -> None:
        """
        Validates an explicitly-provided tarifa in the input.
        Raises HttpError if invalid.
        """
        today = timezone.now().date()
        is_vigente = (
            tarifa.tarifa_base.periodo_inicio <= today
            and (
                tarifa.tarifa_base.periodo_fin is None
                or tarifa.tarifa_base.periodo_fin >= today
            )
        )
        if not is_vigente:
            raise HttpError(400, f"Tarifa {tarifa.id} no está vigente")
        if tarifa.tarifa_base.tipo_liquidacion != TipoLiquidacion.EDIFICACION:
            raise HttpError(400, f"Tarifa {tarifa.id} no es de edificaciones")
    
    @inject
    def __init__(
        self,
        porcentaje_core_service: LiquidacionPorcentajeObraCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        flujo: LiquidacionEdificacionesFlujo,
    ):
        self.porcentaje_core = porcentaje_core_service
        self.general_core = general_core_service
        self.flujo = flujo
    
    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Validates input, resolves tarifas (hybrid), calculates, delegates to Flujo.
        
        Flow:
        1. Validate valor_declarado > 0
        2. Resolve tarifas (auto-fill or explicit validation)
        3. Validate IGV/UIT vigentes exist
        4. Build domain DTO
        5. Delegate to Flujo
        """
        # Step 1: Validation
        valor_declarado = payload_in.liquidacion_especifica.datos.valor_declarado
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        
        # Step 2: Hybrid resolution
        payload_tarifas_ids = [
            str(t.tarifa_porcentaje_obra_id)
            for t in payload_in.liquidacion_especifica.tarifas
        ]
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids)
        
        # Validate each tarifa (only in explicit mode)
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa)
        
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")
        
        # Step 3: Get vigente IGV and UIT
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")
        
        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")
        
        # Step 4: Build domain DTO
        tarifas_aplicadas = [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.id),
                porcentaje_liquidacion=t.porcentaje_liquidacion,
                especialidad_id=str(t.especialidad.id),
                especialidad_nombre=t.especialidad.nombre,
            )
            for t in tarifas
        ]
        
        domain_data = EdificacionesPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                proyecto=payload_in.liquidacion_general.proyecto,
                # FUTURE: when tipo_tramite is added, pass payload_in.tipo_tramite here
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=None,  # FUTURE: activate when frontend sends it
            ),
        )
        
        # Step 5: Delegate to Flujo
        return self.flujo.ejecutar_primera_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
        )

    def obtener_tarifas_vigentes_proceso(self):
        """
        Fetches currently active TarifaPorcentajeObra list for Edificaciones.
        Returns List[TarifaPorcentajeObra].
        """
        return self.porcentaje_core.get_tarifas_porcentaje_vigentes()

    def cotizar_proceso(
        self,
        valor_declarado: Decimal,
        payload_tarifas_ids: List[str],
    ) -> CotizacionPorcentajeObraResult:
        """
        Quote-only calculation. Does NOT persist.
        
        Same hybrid resolution as crear_primera_revision_proceso.
        Returns CotizacionPorcentajeObraResult with totals and per-detalle breakdown.
        """
        # Step 1: Validation
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        
        # Step 2: Hybrid resolution
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids)
        
        # Validate explicit mode
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa)
        
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")
        
        # Step 3: Get vigente IGV and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente")
        
        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")
        
        # Step 4: Calculate
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
        )
        
        # Step 5: Build result
        return CotizacionPorcentajeObraResult(
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado_id=cotizacion.derecho_aplicado_id,
            detalles=[
                CotizacionPorcentajeObraDetalleResult(
                    tarifa_id=d.tarifa_aplicada.tarifa_id,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv,
                    uit=d.uit,
                    total=d.total,
                )
                for d in cotizacion.detalles
            ],
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )
