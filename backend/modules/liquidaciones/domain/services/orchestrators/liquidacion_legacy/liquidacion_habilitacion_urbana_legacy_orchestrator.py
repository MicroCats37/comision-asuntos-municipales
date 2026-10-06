"""
Legacy Orchestrator for Habilitación Urbana (PorMetroCuadrado) primera-revision.

100% additive — no existing orchestrator modified.

Uses legacy core services (T1) for tariff/derecho resolution by fecha_registro.
Cotization is calculated in-orchestrator using legacy tariff/derecho (no vigente lookup).
Delegates to LiquidacionHabilitacionUrbanaFlujo.ejecutar_legacy(...) (T4).
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_m2_core_service import (
    LiquidacionLegacyPorM2CoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_habilitacion_urbana_flujo import (
    LiquidacionHabilitacionUrbanaFlujo,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.habilitacion_urbana_primera_revision_data import (
    HabilitacionUrbanaPrimeraRevisionData,
    LiquidacionEspecificaHabilitacionUrbanaData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
    HabilitacionUrbanaPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import (
    validar_sin_solapamiento,
)


class LiquidacionHabilitacionUrbanaLegacyOrchestrator:
    """
    Legacy orchestrator for Habilitación Urbana (PorMetroCuadrado).

    Mirrors LiquidacionHabilitacionUrbanaOrchestrator but:
    - Resolves tariff and derecho by fecha_registro (not vigente)
    - IGV/UIT resolved by fecha_registro via legacy core service
    - Cotization calculated in-orchestrator using legacy tariff/derecho
    - Delegates to LiquidacionHabilitacionUrbanaFlujo.ejecutar_legacy(...) (T4)
    """

    @inject
    def __init__(
        self,
        legacy_m2_core: LiquidacionLegacyPorM2CoreService,
        legacy_visitas_core: LiquidacionLegacyPorVisitasCoreService,
        general_core: LiquidacionGeneralCoreService,
        flujo: LiquidacionHabilitacionUrbanaFlujo,
    ):
        self.legacy_m2_core = legacy_m2_core
        self.legacy_visitas_core = legacy_visitas_core
        self.general_core = general_core
        self.flujo = flujo

    def cotizar_legacy_proceso(
        self,
        payload,
    ) -> CotizacionM2Result:
        """
        Calculates the Habilitación Urbana cotizacion using historical tariffs by fecha_registro,
        WITHOUT persisting anything.

        Mirrors the resolution steps of crear_legacy_proceso (steps 1-5: fecha_registro,
        validate area > 0, resolve tarifa/derecho by fecha, resolve IGV/UIT by fecha,
        calculate + apply clamping), but STOPS before building the domain DTO and
        does NOT call the flujo. Returns the clamped CotizacionM2Result.
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validation
        area = payload.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Step 3: Resolve tariff and derecho by fecha_registro
        tarifa_bases = self.legacy_m2_core.get_tarifas_base_list(
            TipoLiquidacion.HABILITACION_URBANA, fecha_registro
        )
        validar_sin_solapamiento(tarifa_bases, f"TarifaLiquidacionBase tipo={TipoLiquidacion.HABILITACION_URBANA}")
        tarifa = self.legacy_m2_core.get_tarifa_m2_por_fecha(
            TipoLiquidacion.HABILITACION_URBANA, fecha_registro
        )
        if not tarifa:
            raise HttpError(400, "No hay tarifa M2 vigente para habilitación urbana en la fecha indicada")

        derechos = self.legacy_m2_core.get_derechos_m2_list(fecha_registro)
        validar_sin_solapamiento(derechos, "DerechoPorMetroCuadrado")
        derecho = self.legacy_m2_core.get_derecho_m2_por_fecha(fecha_registro)
        if not derecho:
            raise HttpError(400, "No hay derecho M2 vigente para la fecha indicada")

        # Step 4: Resolve IGV/UIT by fecha_registro
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv or not uit:
            raise HttpError(400, "No hay IGV o UIT vigente para la fecha indicada")

        # Step 5: Calculate cotization (mirrors LiquidacionPorMetroCuadradoCoreService.calcular_cotizacion_m2)
        monto_bruto = Decimal(str(area)) * Decimal(str(tarifa.costo_por_m2))
        igv_porcentaje = Decimal(str(igv.valor))
        total = monto_bruto

        # Derive subtotal and monto_igv
        subtotal = (total / (Decimal("1") + igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        monto_igv = total - subtotal

        cotizacion = CotizacionM2Result(
            area_m2=Decimal(str(area)),
            costo_por_m2=tarifa.costo_por_m2,
            tarifa_id=str(tarifa.id),
            derecho_id=str(derecho.id) if derecho else None,
            minimo=derecho.derecho_minimo if derecho else None,
            maximo=derecho.derecho_maximo if derecho and derecho.derecho_maximo is not None else None,
            monto_bruto=monto_bruto,
            subtotal=subtotal,
            total=total,
            igv_porcentaje=igv_porcentaje,
            monto_igv=monto_igv,
        )

        # Apply min/max clamping on TOTAL (bruto) — Orchestrator owns clamping logic
        if cotizacion.total < cotizacion.minimo:
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.total > cotizacion.maximo:
            cotizacion.total = cotizacion.maximo

        # Re-derive subtotal and monto_igv from clamped total
        cotizacion.subtotal = (cotizacion.total / (Decimal("1") + igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cotizacion.monto_igv = cotizacion.total - cotizacion.subtotal

        return cotizacion

    def crear_legacy_proceso(
        self,
        usuario_id: int,
        payload,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Creates a Habilitación Urbana liquidacion using historical tariffs by fecha_registro.

        Steps:
        1. Extract fecha_registro (default today)
        2. Validate area_solicitada > 0
        3. Resolve tariff and derecho by fecha_registro via legacy core
        4. Resolve IGV/UIT by fecha_registro via legacy core
        5. Calculate cotization in-orchestrator with clamping
        6. Build domain DTO
        7. Delegate to Flujo.ejecutar_legacy(...)
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validation
        area = payload.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Step 3: Resolve tariff and derecho by fecha_registro
        tarifa_bases = self.legacy_m2_core.get_tarifas_base_list(
            TipoLiquidacion.HABILITACION_URBANA, fecha_registro
        )
        validar_sin_solapamiento(tarifa_bases, f"TarifaLiquidacionBase tipo={TipoLiquidacion.HABILITACION_URBANA}")
        tarifa = self.legacy_m2_core.get_tarifa_m2_por_fecha(
            TipoLiquidacion.HABILITACION_URBANA, fecha_registro
        )
        if not tarifa:
            raise HttpError(400, "No hay tarifa M2 vigente para habilitación urbana en la fecha indicada")

        derechos = self.legacy_m2_core.get_derechos_m2_list(fecha_registro)
        validar_sin_solapamiento(derechos, "DerechoPorMetroCuadrado")
        derecho = self.legacy_m2_core.get_derecho_m2_por_fecha(fecha_registro)
        if not derecho:
            raise HttpError(400, "No hay derecho M2 vigente para la fecha indicada")

        # Step 4: Resolve IGV/UIT by fecha_registro
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv or not uit:
            raise HttpError(400, "No hay IGV o UIT vigente para la fecha indicada")

        # Step 5: Calculate cotization — OR use legacy totals bypass
        cotizacion: CotizacionM2Result
        if getattr(payload, "cotizacion_legacy", None) is not None:
            # Legacy totals bypass — use source values directly, NO clamping
            legacy = payload.cotizacion_legacy
            cotizacion = CotizacionM2Result(
                area_m2=Decimal(str(area)),
                costo_por_m2=tarifa.costo_por_m2,
                tarifa_id=str(tarifa.id),
                derecho_id=str(derecho.id) if derecho else None,
                minimo=derecho.derecho_minimo if derecho else None,
                maximo=derecho.derecho_maximo if derecho and derecho.derecho_maximo is not None else None,
                monto_bruto=Decimal(str(area)) * Decimal(str(tarifa.costo_por_m2)),
                subtotal=legacy.sub_total,
                total=legacy.total,
            )
        else:
            # Normal M2 calculation with min/max clamping
            monto_bruto = Decimal(str(area)) * Decimal(str(tarifa.costo_por_m2))
            igv_porcentaje = Decimal(str(igv.valor))
            total = monto_bruto

            # Derive subtotal and monto_igv
            subtotal = (total / (Decimal("1") + igv_porcentaje)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            monto_igv = total - subtotal

            cotizacion = CotizacionM2Result(
                area_m2=Decimal(str(area)),
                costo_por_m2=tarifa.costo_por_m2,
                tarifa_id=str(tarifa.id),
                derecho_id=str(derecho.id) if derecho else None,
                minimo=derecho.derecho_minimo if derecho else None,
                maximo=derecho.derecho_maximo if derecho and derecho.derecho_maximo is not None else None,
                monto_bruto=monto_bruto,
                subtotal=subtotal,
                total=total,
                igv_porcentaje=igv_porcentaje,
                monto_igv=monto_igv,
            )

            # Apply min/max clamping on TOTAL (bruto) — Orchestrator owns clamping logic
            if cotizacion.total < cotizacion.minimo:
                cotizacion.total = cotizacion.minimo
            elif cotizacion.maximo is not None and cotizacion.total > cotizacion.maximo:
                cotizacion.total = cotizacion.maximo

            # Re-derive subtotal and monto_igv from clamped total
            cotizacion.subtotal = (cotizacion.total / (Decimal("1") + igv_porcentaje)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            cotizacion.monto_igv = cotizacion.total - cotizacion.subtotal

        # Step 6: Build domain DTO
        domain_data = HabilitacionUrbanaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload.liquidacion_general.municipalidad_id),
                expediente=payload.liquidacion_general.expediente,
                observacion=payload.liquidacion_general.observacion,
                proyecto=ProyectoData(
                    nombre_propietario=payload.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload.liquidacion_general.proyecto.distrito_id),
                    entidad_razon_social=payload.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
                denominacion_de_proyecto=getattr(
                    payload.liquidacion_general, "denominacion_de_proyecto", None
                ),
                descripcion_legacy=getattr(
                    payload.liquidacion_general, "descripcion_legacy", None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaHabilitacionUrbanaData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        numero_revision = getattr(payload, "numero_revision", 1) or 1
        numero = getattr(payload, "numero", None)

        # Step 7: Delegate to Flujo.ejecutar_legacy (T4)
        return self.flujo.ejecutar_legacy(
            usuario_id=usuario_id,
            data=domain_data,
            igv=igv,
            uit=uit,
            numero_revision=numero_revision,
            fecha_registro=fecha_registro,
            numero=numero,
        )
