"""
Legacy Orchestrator for Impacto Vial (PorcentajeObra) primera-revision.

100% additive — no existing orchestrator modified.

Uses legacy core services (T1) for tariff/derecho resolution by fecha_registro.
Delegates to LiquidacionImpactoVialFlujo.ejecutar_legacy(...) (T4).
"""
from datetime import date
from decimal import Decimal
from typing import List

from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_porcentaje_core_service import (
    LiquidacionLegacyPorPorcentajeCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_impacto_vial_flujo import (
    LiquidacionImpactoVialFlujo,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
    ContactoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    CotizacionPorcentajeObraData,
    DatosPorcentajeObra,
    LiquidacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.primera_revision_data import (
    LiquidacionEspecificaPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
    LiquidacionEspecificaPrimeraRevisionResult,
)
from modules.liquidaciones.domain.services.orchestrators._shared.liquidacion_po_validation import (
    LiquidacionPOValidationMixin,
)
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import (
    validar_sin_solapamiento,
)


class LiquidacionImpactoVialLegacyOrchestrator(LiquidacionPOValidationMixin):
    """
    Legacy orchestrator for Impacto Vial (PorcentajeObra).

    Mirrors LiquidacionImpactoVialOrchestrator but:
    - Resolves tariffs and derechos by fecha_registro (not vigente)
    - IGV/UIT resolved by fecha_registro via legacy core service
    - Delegates to LiquidacionImpactoVialFlujo.ejecutar_legacy(...) (T4)
    """

    @inject
    def __init__(
        self,
        legacy_po_core: LiquidacionLegacyPorPorcentajeCoreService,
        legacy_visitas_core: LiquidacionLegacyPorVisitasCoreService,
        general_core: LiquidacionGeneralCoreService,
        porcentaje_core: LiquidacionPorcentajeObraCoreService,
        flujo: LiquidacionImpactoVialFlujo,
    ):
        self.legacy_po_core = legacy_po_core
        self.legacy_visitas_core = legacy_visitas_core
        self.general_core = general_core
        self.porcentaje_core = porcentaje_core
        self.flujo = flujo

    def cotizar_legacy_proceso(
        self,
        payload,
    ) -> CotizacionPorcentajeObraData:
        """
        Calculates the Impacto Vial cotizacion using historical tariffs by fecha_registro,
        WITHOUT persisting anything.

        Mirrors the resolution steps of crear_legacy_proceso (steps 1-4),
        then calls the pure calcular_cotizacion_po. Used by the legacy ingest script to
        compare calculated vs expected values BEFORE inserting.

        Returns CotizacionPorcentajeObraData with porcentaje_liquidacion, total_subtotal, total.
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validation
        valor_declarado = payload.liquidacion_especifica.datos.valor_declarado
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 3: Resolve tarifas by fecha_registro
        input_tarifas = payload.liquidacion_especifica.tarifas
        tarifas = self.legacy_po_core.get_tarifa_por_fecha(
            TipoLiquidacion.IMPACTO_VIAL, fecha_registro
        )
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para impacto vial en la fecha indicada")

        tarifa_map = {str(t.id): t for t in tarifas}

        # Step 4: Resolve IGV/UIT + derecho by fecha_registro
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv or not uit:
            raise HttpError(400, "No hay IGV o UIT vigente para la fecha indicada")

        derecho = self.legacy_po_core.get_derecho_porcentaje_por_fecha(fecha_registro)
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente para la fecha indicada")

        # Build TarifaPorcentajeObraAplicada DTOs (auto-fill: tarifa x especialidades)
        especialidades = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.IMPACTO_VIAL, fecha=fecha_registro
        )
        tarifas_dedup = list({t.tarifa_base_id: t for t in tarifas}.values())
        tarifas_aplicadas = [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.id),
                porcentaje_liquidacion=t.porcentaje_liquidacion,
                especialidad_id=str(esp.especialidad_id),
                especialidad_nombre=esp.especialidad.nombre if esp.especialidad else None,
            )
            for t in tarifas_dedup
            for esp in especialidades
        ]

        # Pure calculation — no persistence
        return self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas_aplicadas,
            igv_porcentaje=Decimal(str(igv.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit.valor)),
        )

    def crear_legacy_proceso(
        self,
        usuario_id: int,
        payload,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Creates an Impacto Vial liquidacion using historical tariffs by fecha_registro.

        Steps:
        1. Extract fecha_registro (default today)
        2. Validate valor_declarado > 0
        3. Resolve tarifas and derecho by fecha_registro via legacy core
        4. Resolve IGV/UIT by fecha_registro via legacy core
        5. Build domain DTO
        6. Delegate to Flujo.ejecutar_legacy(...)
        """
        # Step 1: fecha_registro
        fecha_registro = (
            payload.liquidacion_general.fecha_registro
            if hasattr(payload.liquidacion_general, "fecha_registro")
            and payload.liquidacion_general.fecha_registro
            else date.today()
        )

        # Step 2: Validation
        valor_declarado = payload.liquidacion_especifica.datos.valor_declarado
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 3: Resolve tarifas by fecha_registro
        input_tarifas = payload.liquidacion_especifica.tarifas
        payload_tarifas_ids = list(
            dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in input_tarifas)
        )
        tarifas = self.legacy_po_core.get_tarifa_por_fecha(
            TipoLiquidacion.IMPACTO_VIAL, fecha_registro
        )

        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.IMPACTO_VIAL)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para impacto vial en la fecha indicada")

        # Build a map of tarifa_id -> ORM object for quick lookup
        tarifa_map = {str(t.id): t for t in tarifas}

        # Step 4: Resolve IGV/UIT by fecha_registro
        igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        if not igv or not uit:
            raise HttpError(400, "No hay IGV o UIT vigente para la fecha indicada")

        derecho = self.legacy_po_core.get_derecho_porcentaje_por_fecha(fecha_registro)
        validar_sin_solapamiento(
            self.legacy_po_core.get_derechos_porcentaje_list(fecha_registro),
            "DerechoPorcentajeObra",
        )
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente para la fecha indicada")

        # Build TarifaPorcentajeObraAplicada DTOs with explicit especialidad from input
        if input_tarifas:
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    porcentaje_liquidacion=tarifa_map[
                        str(t.tarifa_porcentaje_obra_id)
                    ].porcentaje_liquidacion,
                    especialidad_id=str(t.especialidad_id),
                    especialidad_nombre=None,
                )
                for t in input_tarifas
            ]
        else:
            # Auto-fill: combine one tarifa per base x every vigente especialidad
            especialidades = self._obtener_especialidades_vigentes_para_tipo(
                TipoLiquidacion.IMPACTO_VIAL, fecha=fecha_registro
            )
            tarifas_dedup = list({t.tarifa_base_id: t for t in tarifas}.values())
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.id),
                    porcentaje_liquidacion=t.porcentaje_liquidacion,
                    especialidad_id=str(esp.especialidad_id),
                    especialidad_nombre=esp.especialidad.nombre if esp.especialidad else None,
                )
                for t in tarifas_dedup
                for esp in especialidades
            ]

        # Step 5: Build domain DTO
        domain_data = LiquidacionEspecificaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload.liquidacion_general.municipalidad_id),
                expediente=payload.liquidacion_general.expediente,
                observacion=payload.liquidacion_general.observacion,
                retencion=getattr(payload.liquidacion_general, "retencion", False),
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
                contacto=(
                    ContactoData(
                        nombres=payload.liquidacion_general.contacto.nombres,
                        apellidos=payload.liquidacion_general.contacto.apellidos,
                        dni=payload.liquidacion_general.contacto.dni,
                        cargo=payload.liquidacion_general.contacto.cargo,
                        telefono=payload.liquidacion_general.contacto.telefono,
                        celular=payload.liquidacion_general.contacto.celular,
                        email=payload.liquidacion_general.contacto.email,
                    )
                    if payload.liquidacion_general.contacto
                    else None
                ),
                denominacion_de_proyecto=getattr(
                    payload.liquidacion_general, "denominacion_de_proyecto", None
                ),
                descripcion_legacy=getattr(
                    payload.liquidacion_general, "descripcion_legacy", None
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=None,
                override_subtotal=(
                    payload.cotizacion_legacy.sub_total
                    if getattr(payload, "cotizacion_legacy", None) is not None
                    else None
                ),
                override_total=(
                    payload.cotizacion_legacy.total
                    if getattr(payload, "cotizacion_legacy", None) is not None
                    else None
                ),
            ),
        )

        numero_revision = getattr(payload, "numero_revision", 1) or 1

        # Step 6: Delegate to Flujo.ejecutar_legacy (T4)
        return self.flujo.ejecutar_legacy(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit.valor)),
            numero_revision=numero_revision,
            fecha_registro=fecha_registro,
            legacy_visitas_core=self.legacy_visitas_core,
        )
