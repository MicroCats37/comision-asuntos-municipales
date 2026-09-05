"""
Legacy Orchestrator for Inspección de Obra (Visitas) primera-revision desde liquidacion previa.

100% additive — no existing orchestrator modified.

Uses legacy core services (T1) for tariff/IGV/UIT resolution by fecha_registro.
Delegates to LiquidacionInspeccionObraFlujo.ejecutar_legacy_desde_previa(...) (T4).

NOTE: Inspección de Obra always inherits from a previous liquidacion (Edificación or HU).
The legacy schema includes liquidacion_previa_id for this purpose.
"""
import uuid
from datetime import date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_inspeccion_obra_flujo import (
    LiquidacionInspeccionObraFlujo,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    DatosVisitas,
    TarifaVisitas,
    LiquidacionCategoriaVisitasData,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraNuevaRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionVisitasResult
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import (
    validar_sin_solapamiento,
)


class LiquidacionInspeccionObraLegacyOrchestrator:
    """
    Legacy orchestrator for Inspección de Obra (Visitas).

    Mirrors LiquidacionInspeccionObraOrchestrator.crear_primera_revision_desde_previa_proceso but:
    - Resolves tariff by fecha_registro (not vigente)
    - IGV/UIT resolved by fecha_registro via legacy core service
    - Delegates to LiquidacionInspeccionObraFlujo.ejecutar_legacy_desde_previa(...) (T4)
    """

    @inject
    def __init__(
        self,
        legacy_visitas_core: LiquidacionLegacyPorVisitasCoreService,
        general_core: LiquidacionGeneralCoreService,
        flujo: LiquidacionInspeccionObraFlujo,
    ):
        self.legacy_visitas_core = legacy_visitas_core
        self.general_core = general_core
        self.flujo = flujo

    def cotizar_legacy_proceso(
        self,
        payload,
    ) -> CotizacionVisitasResult:
        """
        Calculates the Inspección de Obra cotizacion using historical tariffs by fecha_registro,
        WITHOUT persisting anything.

        Mirrors the resolution steps of crear_legacy_proceso (steps 1, 3, 4, 5:
        fecha_registro, validate cantidad_visitas > 0, resolve tarifa by fecha,
        resolve IGV/UIT by fecha, calculate subtotal), but STOPS before building
        the domain DTO and does NOT call the flujo. Returns CotizacionVisitasResult.

        Formula: subtotal = cantidad_visitas * (porcentaje_uit * uit_valor)
                 total = subtotal * (1 + igv_valor)
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validate cantidad_visitas > 0 (same as crear_legacy_proceso step 3)
        cantidad_visitas = payload.liquidacion_especifica.datos.cantidad_visitas
        if cantidad_visitas <= 0:
            raise HttpError(400, "cantidad_visitas debe ser mayor a 0")

        # Step 3: Resolve tariff by fecha_registro (same as crear_legacy_proceso step 4)
        tarifas = self.legacy_visitas_core.get_tarifa_visitas_por_fecha(
            TipoLiquidacion.INSPECCION_OBRA, fecha_registro
        )
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para inspección de obra en la fecha indicada")

        tarifa_id_str = str(payload.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = next((t for t in tarifas if str(t.id) == tarifa_id_str), None)
        if not tarifa:
            raise HttpError(404, f"No se encontró tarifa válida para ID {tarifa_id_str}")

        # Step 4: Resolve IGV/UIT by fecha_registro (same as crear_legacy_proceso step 5)
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv:
            raise HttpError(404, "No hay IGV vigente para la fecha indicada")
        if not uit:
            raise HttpError(404, "No hay UIT vigente para la fecha indicada")

        # Calculate: subtotal = cantidad_visitas * (porcentaje_uit * uit_valor)
        costo_por_visita = tarifa.porcentaje_uit * uit.valor
        subtotal = Decimal(str(cantidad_visitas)) * costo_por_visita
        igv_valor = igv.valor
        total = subtotal * (Decimal("1") + igv_valor)

        return CotizacionVisitasResult(
            cantidad_visitas=cantidad_visitas,
            categoria=tarifa.categoria_visitas,
            costo_por_visita=costo_por_visita,
            tarifa_id=str(tarifa.id),
            monto_bruto=subtotal,
            subtotal=subtotal,
            total=total,
            uit={"id": str(uit.id), "valor": float(uit.valor)},
            igv={"id": str(igv.id), "valor": float(igv.valor)},
        )

    def crear_legacy_proceso(
        self,
        usuario_id: int,
        payload,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Creates an Inspección de Obra legacy liquidacion inheriting from a previous liquidacion.

        Steps:
        1. Extract fecha_registro (default today)
        2. Validate liquidacion_previa_id and type (EDIFICACION or HABILITACION_URBANA)
        3. Validate cantidad_visitas > 0
        4. Resolve tariff by fecha_registro via legacy core
        5. Resolve IGV/UIT by fecha_registro via legacy core
        6. Validate inspector exists
        7. Build domain DTO (inheriting proyecto/entidad from previa)
        8. Delegate to Flujo.ejecutar_legacy_desde_previa(...)
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validate liquidacion_previa exists and is EDIFICACION or HABILITACION_URBANA
        previa_id = payload.liquidacion_previa_id
        try:
            previa = self.general_core.get_liquidacion_previa_para_io(previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, f"Liquidación previa {previa_id} no encontrada")

        tipo_previo = previa.tipo_liquidacion.codigo
        if tipo_previo not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            raise HttpError(
                400,
                f"La liquidación previa debe ser Edificación o Habilitación Urbana. "
                f"Se proporcionó: {tipo_previo}",
            )

        # Step 3: Validation
        cantidad_visitas = payload.liquidacion_especifica.datos.cantidad_visitas
        if cantidad_visitas <= 0:
            raise HttpError(400, "cantidad_visitas debe ser mayor a 0")

        # Step 4: Resolve tariff by fecha_registro
        tarifa_bases = self.legacy_visitas_core.get_tarifas_base_list(
            TipoLiquidacion.INSPECCION_OBRA, fecha_registro
        )
        validar_sin_solapamiento(tarifa_bases, f"TarifaLiquidacionBase tipo={TipoLiquidacion.INSPECCION_OBRA}")
        tarifas = self.legacy_visitas_core.get_tarifa_visitas_por_fecha(
            TipoLiquidacion.INSPECCION_OBRA, fecha_registro
        )
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para inspección de obra en la fecha indicada")

        # Find the specific tariff by ID from input
        tarifa_id_str = str(payload.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = next((t for t in tarifas if str(t.id) == tarifa_id_str), None)
        if not tarifa:
            raise HttpError(404, f"No se encontró tarifa válida para ID {tarifa_id_str}")

        # Step 5: Resolve IGV/UIT by fecha_registro
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv:
            raise HttpError(404, "No hay IGV vigente para la fecha indicada")
        if not uit:
            raise HttpError(404, "No hay UIT vigente para la fecha indicada")

        # Step 6: Validate inspector exists
        inspector_id = payload.liquidacion_especifica.inspector_id
        try:
            inspector = Inspector.objects.get(id=inspector_id)
        except ObjectDoesNotExist:
            raise HttpError(404, f"No se encontró inspector con ID {inspector_id}")

        # Step 7: Build domain DTO
        # IO inherits proyecto/entidad from previa (not created new)
        gen_data = payload.liquidacion_especifica
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=cantidad_visitas,
                categoria=gen_data.datos.categoria,
            ),
            tarifa=TarifaVisitas(tarifa_visitas_id=str(gen_data.tarifa.tarifa_visitas_id)),
        )

        domain_data = InspeccionObraNuevaRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=previa.expediente,
                observacion=previa.observacion,
                retencion=previa.retencion,
                proyecto=ProyectoData(
                    nombre_propietario=previa.proyecto.nombre_propietario,
                    direccion=previa.proyecto.direccion,
                    distrito_id=str(previa.proyecto.distrito_id),
                    entidad_razon_social=getattr(previa.proyecto, "entidad_razon_social", None),
                    entidad=EntidadData(
                        tipo_documento=getattr(previa.proyecto, "entidad_tipo_documento", None) or "",
                        numero_documento=getattr(previa.proyecto, "entidad_numero_documento", None) or "",
                    ),
                ),
                denominacion_de_proyecto=getattr(
                    payload.liquidacion_general, "denominacion_de_proyecto", None
                ),
                descripcion_legacy=getattr(
                    payload.liquidacion_general, "descripcion_legacy", None
                ),
            ),
            liquidacion_especifica=visitas_data,
            inspector_id=inspector_id,
        )

        numero_revision = getattr(payload, "numero_revision", 1) or 1

        # Step 8: Delegate to Flujo.ejecutar_legacy_desde_previa (T4)
        return self.flujo.ejecutar_legacy_desde_previa(
            usuario_id=usuario_id,
            data=domain_data,
            liquidacion_previa=previa,
            inspector=inspector,
            igv=igv,
            uit=uit,
            numero_revision=numero_revision,
            fecha_registro=fecha_registro,
        )
