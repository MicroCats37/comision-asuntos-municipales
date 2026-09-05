"""
Orchestrator for Taludes (PorcentajeObra) first revision.

Validates input, applies per-detail clamping,
maps Presentation Schema -> Domain DTO.

Architecture: Orchestrator owns business rules (clamping). No @transaction.atomic.
"""
import uuid
from decimal import Decimal
from typing import List, Optional
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
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_taludes_flujo import (
    LiquidacionTaludesFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
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
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
    CotizacionPorcentajeObraDetalleResult,
    EspecialidadResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraTarifaIn,
)
from django.core.exceptions import ObjectDoesNotExist
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError
from modules.liquidaciones.domain.services.orchestrators._shared import LiquidacionPOValidationMixin
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import validar_tarifa_unica_por_base


class LiquidacionTaludesOrchestrator(LiquidacionPOValidationMixin):
    """
    Orchestrator for Taludes (PorcentajeObra).

    Mirrors the Edificaciones pattern but for TALUDES.
    Uses LiquidacionPOValidationMixin for shared validation helpers.
    """

    @inject
    def __init__(
        self,
        porcentaje_core_service: LiquidacionPorcentajeObraCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        general_orchestrator: LiquidacionGeneralOrchestrator,
        flujo: LiquidacionTaludesFlujo,
    ):
        self.porcentaje_core = porcentaje_core_service
        self.general_core = general_core_service
        self.general_orchestrator = general_orchestrator
        self.flujo = flujo

    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
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
        # With tarifa-unica-especialidades: each input entry brings its own
        # especialidad_id (from LiquidacionEspecialidadDisponibles).
        input_tarifas = payload_in.liquidacion_especifica.tarifas
        payload_tarifas_ids = list(dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in input_tarifas))
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.TALUDES)

        # Validate each tarifa (only in explicit mode)
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.TALUDES)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para taludes")

        # Build a map of tarifa_id -> ORM object for quick lookup
        tarifa_map = {str(t.id): t for t in tarifas}

        # Step 3: Get vigente IGV and UIT
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 4: Build domain DTOs with explicit especialidad from INPUT
        if input_tarifas:
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    porcentaje_liquidacion=tarifa_map[str(t.tarifa_porcentaje_obra_id)].porcentaje_liquidacion,
                    especialidad_id=str(t.especialidad_id),
                    especialidad_nombre=None,
                )
                for t in input_tarifas
            ]
        else:
            # Auto-fill: combine one tarifa per base x every vigente especialidad.
            # In tarifa-unica design there is ONE tarifa per TarifaLiquidacionBase/periodo,
            # so deduplicate by tarifa_base to avoid duplicate (liquidacion_porcentaje, especialidad).
            especialidades = self._obtener_especialidades_vigentes_para_tipo(TipoLiquidacion.TALUDES)
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

        domain_data = LiquidacionEspecificaPrimeraRevisionData(
liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id),
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=None,
            ),
        )

        # Step 5: Delegate to Flujo
        return self.flujo.ejecutar_primera_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
        )

    def obtener_tarifas_vigentes_proceso(self, fecha=None):
        """
        Fetches currently active (or historical at fecha) TarifaPorcentajeObra list
        and available LiquidacionEspecialidadDisponibles for Taludes.

        With tarifa-unica-especialidades: returns a tuple of
        (tarifas, especialidades_disponibles) since the single tariff
        no longer carries an especialidad FK.

        Args:
            fecha: Optional date to fetch vigentes at that date. Defaults to today.
        """
        tarifas = self.porcentaje_core.get_tarifas_porcentaje_vigentes(
            TipoLiquidacion.TALUDES, fecha=fecha
        )
        if fecha is None:
            validar_tarifa_unica_por_base(tarifas, TipoLiquidacion.TALUDES)
        especialidades = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.TALUDES, fecha=fecha
        )
        return tarifas, especialidades

    def cotizar_proceso(
        self,
        valor_declarado: Decimal,
        tarifas_input: List[LiquidacionPorcentajeObraTarifaIn],
    ) -> CotizacionPorcentajeObraResult:
        """
        Quote-only calculation. Does NOT persist.

        Same hybrid resolution as crear_primera_revision_proceso.
        Returns CotizacionPorcentajeObraResult with totals and per-detalle breakdown.
        """
        # Step 1: Validation
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 2: Hybrid resolution (dedupe IDs for ORM query)
        payload_tarifas_ids = list(dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in tarifas_input))
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.TALUDES)

        # Validate explicit mode
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.TALUDES)
        
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para taludes")
        
        # Build a map of tarifa_id -> ORM object for quick lookup
        tarifa_map = {str(t.id): t for t in tarifas}
        
        # Step 3: Get vigente IGV, UIT and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente")
        if not uit_vigente:
            raise HttpError(400, "No hay UIT vigente configurado")
        
        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")
        
        # Step 4: Build DTOs with explicit especialidad from input
        if tarifas_input:
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    porcentaje_liquidacion=tarifa_map[str(t.tarifa_porcentaje_obra_id)].porcentaje_liquidacion,
                    especialidad_id=str(t.especialidad_id),
                    especialidad_nombre=None,
                )
                for t in tarifas_input
            ]
        else:
            # Auto-fill: combine one tarifa per base x every vigente especialidad.
            # In tarifa-unica design there is ONE tarifa per TarifaLiquidacionBase/periodo,
            # so deduplicate by tarifa_base to avoid duplicate (liquidacion_porcentaje, especialidad).
            especialidades = self._obtener_especialidades_vigentes_para_tipo(TipoLiquidacion.TALUDES)
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
        
        # Step 5: Calculate with DTOs (not ORM objects)
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas_aplicadas,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
        )
        
        # Step 6: Build result
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
                    especialidad=EspecialidadResult(
                        id=d.tarifa_aplicada.especialidad_id,
                        nombre=d.tarifa_aplicada.especialidad_nombre or "",
                    ) if d.tarifa_aplicada.especialidad_id else None,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                )
                for d in cotizacion.detalles
            ],
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )

    def listar_liquidaciones(
        self, page: int, page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
    ) -> tuple[List[LiquidacionEspecificaPrimeraRevisionResult], int]:
        """
        Returns paginated LiquidacionEspecificaPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionEspecificaPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core.list_liquidaciones_taludes_paginated(
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

        # Build LiquidacionEspecificaPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[LiquidacionEspecificaPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_taludes_result(lg))

        return domain_results, total

    def _build_taludes_result(self, lg) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to LiquidacionEspecificaPrimeraRevisionResult domain DTO.

        Delegates LiquidacionGeneralResult construction to general_core.build_general_result().
        Only the type-specific fields (taludes, liquidacion_porcentaje_obra) are built here.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
            LiquidacionEspecificaResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
            LiquidacionPorcentajeObraResult,
            DetallePorcentajeObraResult,
            EspecialidadResult,
        )

        # Delegate general result construction to core (NO more duplicate inline mapping)
        usuario_id = lg.usuario_creador.id if lg.usuario_creador else 0

        # Build contacto_result from lg.contacto
        contacto_result = None
        if lg.contacto:
            contacto_result = ContactoResult(
                id=str(lg.contacto.id),
                nombres=lg.contacto.nombres,
                apellidos=lg.contacto.apellidos,
                dni=lg.contacto.dni,
                cargo=lg.contacto.cargo,
                telefono=lg.contacto.telefono,
                celular=lg.contacto.celular,
                email=lg.contacto.email,
            )

        general_result = self.general_core.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            codigo_cta=self.general_core.get_codigo_cta(lg.tipo_liquidacion),
        )

        # Type-specific: Taludes
        taludes = lg.taludes
        especifica_result = LiquidacionEspecificaResult(
            id=str(taludes.id),
            numero=taludes.numero,
        )

        lpo = lg.liquidacion_porcentaje_obra
        tipo_result = LiquidacionPorcentajeObraResult(
            id=str(lpo.id),
            liquidacion_general_id=str(lpo.liquidacion_general_id),
            tipo_tramite=lpo.tipo_tramite,
            valor_declarado=lpo.valor_declarado,
            porcentaje_liquidacion=lpo.porcentaje_liquidacion,
            derecho_minimo=lpo.derecho_minimo,
            derecho_maximo=lpo.derecho_maximo,
            porcentaje_minimo_uit=lpo.porcentaje_minimo_uit,
            derecho_aplicado_id=str(lpo.derecho_aplicado_id),
            detalles=[
                DetallePorcentajeObraResult(
                    id=str(d.id),
                    tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                    especialidad=EspecialidadResult(
                        id=str(d.especialidad_id),
                        nombre=getattr(d.especialidad, 'nombre', '') or '',
                    ) if d.especialidad_id else None,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                )
                for d in lpo.detalles.all()
            ],
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Returns a single LiquidacionEspecificaPrimeraRevisionResult for Taludes by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core.get_liquidacion_taludes_by_id(liquidacion_id)
            return self._build_taludes_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

    def recalcular_po(
        self,
        liquidacion_id: uuid.UUID,
        valor_declarado=None,
        tarifas=None,
        liquidacion_general=None,
        liquidacion_tipo=None,
    ):
        """
        PATCH recalculation for Taludes (PO motor).

        Supports two input formats:
        1. Flat (legacy): valor_declarado + tarifas directly
        2. Wrapper (current): liquidacion_general + liquidacion_tipo

        If liquidacion_general is provided, calls general update orchestrator.
        If liquidacion_tipo is provided, delegates to LiquidacionPatchPorcentajeObraService.
        Both can be provided in one call for atomic update.

        Args:
            liquidacion_id: UUID of the LiquidacionGeneral to recalculate.
            valor_declarado: New valor_declarado (flat format, None = preserve current).
            tarifas: List of TarifaPatchInput (flat format, None = preserve current).
            liquidacion_general: Optional dict with general fields (wrapper format).
            liquidacion_tipo: Optional dict with tipo fields (wrapper format).

        Returns:
            LiquidacionEspecificaPrimeraRevisionResult with updated values.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
            ConflictError: If estado == PAGADA.
        """
        from django.db import transaction
        from core.exceptions import ConflictError
        from modules.liquidaciones.domain.constants import EstadoLiquidacion
        from modules.liquidaciones.domain.services.core.liquidacion_patch_porcentaje_obra_service import (
            LiquidacionPatchPorcentajeObraService,
            PatchPorcentajeObraInput,
            TarifaPatchInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_taludes_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

        # 2. Guard: only PENDIENTE allows updates (applies to BOTH general and tipo)
        if lg.estado == EstadoLiquidacion.PAGADA:
            raise ConflictError(
                message="No se puede editar una liquidación en estado PAGADA.",
                code="LIQUIDACION_PAGADA_NOT_EDITABLE",
            )

        # 3. Handle wrapper format: extract from liquidacion_general + liquidacion_tipo
        if liquidacion_tipo is not None:
            # Wrapper format: extract from nested structure
            tipo_datos = liquidacion_tipo.get("datos") or {}
            tipo_tarifas = liquidacion_tipo.get("tarifas")
            # Map wrapper field names to flat format
            vd = tipo_datos.get("valor_declarado", valor_declarado)
            # Map wrapper tarifa field names (tarifa_porcentaje_obra_id -> tarifa_id)
            if tipo_tarifas is not None:
                tarifas_input = [
                    TarifaPatchInput(
                        tarifa_id=str(t.get("tarifa_porcentaje_obra_id") or t.get("tarifa_id")),
                        especialidad_id=str(t["especialidad_id"]),
                    )
                    for t in tipo_tarifas
                ]
            else:
                tarifas_input = tarifas
        else:
            # Flat format: use params directly
            vd = valor_declarado
            if tarifas is not None:
                tarifas_input = [
                    TarifaPatchInput(tarifa_id=str(t.tarifa_id), especialidad_id=str(t.especialidad_id))
                    for t in tarifas
                ]
            else:
                tarifas_input = None

        # 4. Execute updates in a single transaction
        patch_service = LiquidacionPatchPorcentajeObraService()
        with transaction.atomic():
            # 4a. Update general fields if provided
            # Pass lg directly to avoid re-fetch which creates stale reference bug
            # when combined with tipo update (Bug #general-wrapper-bug)
            if liquidacion_general is not None:
                self.general_orchestrator.actualizar_liquidacion_general_proyecto_municipalidad(
                    liquidacion=lg,
                    expediente=liquidacion_general.get("expediente"),
                    observacion=liquidacion_general.get("observacion"),
                    retencion=liquidacion_general.get("retencion"),
                    municipalidad_id=liquidacion_general.get("municipalidad_id"),
                    proyecto_data=liquidacion_general.get("proyecto"),
                    denominacion_de_proyecto=liquidacion_general.get("denominacion_de_proyecto"),
                    contacto_data=liquidacion_general.get("contacto"),
                )

            # 4b. Update tipo fields if provided
            if vd is not None or tarifas_input is not None:
                patch_input = PatchPorcentajeObraInput(
                    valor_declarado=vd,
                    tarifas=tarifas_input,
                )
                patch_service.recalcular(lg, patch_input)

        # 5. Refresh and return built result
        lg.refresh_from_db()
        return self._build_taludes_result(lg)

    def cotizar_edicion_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload_in: "CotizarEdicionPOWrapperIn",
    ) -> "CotizacionPorcentajeObraResult":
        """
        Read-only quote for editing an existing Taludes liquidacion.

        Uses historical financial values from LiquidacionGeneral.fecha_registro.
        Does NOT persist any changes.

        Args:
            liquidacion_id: UUID of the existing LiquidacionGeneral.
            payload_in: Typed wrapper with liquidacion_tipo.datos and liquidacion_tipo.tarifas.

        Returns:
            CotizacionPorcentajeObraResult with the calculated quote.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
        """
        from django.core.exceptions import ObjectDoesNotExist
        from modules.liquidaciones.domain.services.core.liquidacion_cotizar_edicion_service import (
            LiquidacionCotizarEdicionPOService,
            CotizarEdicionPOInput,
            CotizarEdicionPOTarifaInput,
        )
        from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
            CotizarEdicionPOWrapperIn,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_taludes_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

        # 2. Extract fields from typed wrapper
        tipo_datos = payload_in.liquidacion_tipo.datos
        tipo_tarifas = payload_in.liquidacion_tipo.tarifas

        vd = tipo_datos.valor_declarado
        if vd is not None and vd <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        tarifas_input: Optional[List[CotizarEdicionPOTarifaInput]] = None
        if tipo_tarifas:
            tarifas_input = [
                CotizarEdicionPOTarifaInput(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    especialidad_id=str(t.especialidad_id),
                )
                for t in tipo_tarifas
            ]

        patch_input = CotizarEdicionPOInput(
            valor_declarado=vd,
            tarifas=tarifas_input,
        )

        # 3. Quote (read-only, no DB mutation)
        quote_service = LiquidacionCotizarEdicionPOService()
        return quote_service.cotizar_edicion(lg, patch_input)



