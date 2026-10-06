"""
LiquidacionHabilitacionUrbanaOrchestrator — sync facade for Habilitacion Urbana.

Thin sync facade. Validates input and delegates to Core/Flujo for calculation.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from injector import inject
from ninja.errors import HttpError
from django.core.exceptions import ObjectDoesNotExist

from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_habilitacion_urbana_flujo import (
    LiquidacionHabilitacionUrbanaFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaInput,
    LiquidacionHabilitacionUrbanaRelacionadaInput,
    LiquidacionHabilitacionUrbanaNuevaRevisionInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.habilitacion_urbana_primera_revision_data import (
    HabilitacionUrbanaPrimeraRevisionData,
    LiquidacionEspecificaHabilitacionUrbanaData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
    HabilitacionUrbanaPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
    ProyectoData,
    EntidadData,
    ContactoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError


class LiquidacionHabilitacionUrbanaOrchestrator:
    """
    Sync facade for Habilitacion Urbana liquidacion.

    Responsibilities:
    - Input validation (area_solicitada > 0)
    - Delegates to M2 Core service for calculation
    """

    @inject
    def __init__(
        self,
        m2_core_service: LiquidacionPorMetroCuadradoCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        general_orchestrator: LiquidacionGeneralOrchestrator,
        flujo: LiquidacionHabilitacionUrbanaFlujo,
    ):
        self.m2_core_service = m2_core_service
        self.general_core_service = general_core_service
        self.general_orchestrator = general_orchestrator
        self.flujo = flujo

    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in: LiquidacionHabilitacionUrbanaInput,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Valida y orquesta la creacion de Habilitacion Urbana (Primera Revision).
        """
        area = payload_in.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Resolve IGV vigente
        igv_vigente = self.general_core_service.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")
        igv_porcentaje = Decimal(str(igv_vigente.valor))

        # Calculate M2 cotizacion with IGV
        cotizacion = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area,
            tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id),
            igv_porcentaje=igv_porcentaje,
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

        # Mapear Presentation Schema -> Domain DTO (with pre-clamped cotizacion)
        domain_data = HabilitacionUrbanaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id) if payload_in.liquidacion_general.proyecto.distrito_id else None,
                    urbanizacion=payload_in.liquidacion_general.proyecto.urbanizacion,
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    )
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaHabilitacionUrbanaData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        response = self.flujo.ejecutar_primera_revision(usuario_id=usuario_id, data=domain_data)

        return response

    def crear_relacionada_proceso(
        self,
        usuario_id: int,
        payload_in: "LiquidacionHabilitacionUrbanaRelacionadaInput",
        liquidacion_previa_id: uuid.UUID,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Validates and creates a related Habilitacion Urbana liquidacion with numero_revision=1
        for an existing HU liquidacion.

        The new liquidacion is related to the previous one via the relation group,
        but has its own numero_revision=1 (not a subsequent revision like /nueva-revision).
        """
        # Step 1: Validate liquidacion_previa exists and is HU
        try:
            previa = self.general_core_service.get_liquidacion_hu_by_id(liquidacion_previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, "Liquidación previa no encontrada.")

        # Step 2: Validate area_solicitada > 0
        area = payload_in.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Step 3: Calculate M2 cotizacion with IGV
        igv_vigente = self.general_core_service.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")
        igv_porcentaje = Decimal(str(igv_vigente.valor))

        cotizacion = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area,
            tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id),
            igv_porcentaje=igv_porcentaje,
        )

        # Apply min/max clamping on TOTAL (bruto)
        if cotizacion.total < cotizacion.minimo:
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.total > cotizacion.maximo:
            cotizacion.total = cotizacion.maximo

        # Re-derive subtotal and monto_igv from clamped total
        cotizacion.subtotal = (cotizacion.total / (Decimal("1") + igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cotizacion.monto_igv = cotizacion.total - cotizacion.subtotal

        # Step 4: Build domain DTO
        domain_data = HabilitacionUrbanaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id) if payload_in.liquidacion_general.proyecto.distrito_id else None,
                    urbanizacion=payload_in.liquidacion_general.proyecto.urbanizacion,
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    )
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaHabilitacionUrbanaData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        # Step 5: Delegate to Flujo
        return self.flujo.ejecutar_relacionada(
            usuario_id=usuario_id,
            data=domain_data,
            liquidacion_previa=previa,
        )

    def crear_nueva_revision_proceso(
        self,
        usuario_id: int,
        payload_in: "LiquidacionHabilitacionUrbanaNuevaRevisionInput",
        liquidacion_previa_id: uuid.UUID,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Validates and creates a new revision (3 or 5) for an existing HU liquidacion.

        Validations:
        - liquidacion_previa_id exists and is HU
        - numero_revision follows pattern: previa + 2 (1→3, 3→5)
        - MAX_REVISIONES not exceeded
        - area_solicitada > 0
        """
        # Step 1: Validate liquidacion_previa exists and is HU
        try:
            previa = self.general_core_service.get_liquidacion_hu_by_id(liquidacion_previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, "Liquidación previa no encontrada.")

        # Step 2: Calculate new numero_revision
        nueva_revision_numero = previa.numero_revision + 2
        MAX_REVISIONES = 5
        if nueva_revision_numero > MAX_REVISIONES:
            raise HttpError(400, f"MAX_REVISIONES={MAX_REVISIONES} excedido. No se puede crear revisión {nueva_revision_numero}")

        # Step 3: Validate odd revision numbers
        if nueva_revision_numero % 2 == 0:
            raise HttpError(400, f"Solo se permiten revisiones impares (1, 3, 5). No se puede crear revisión {nueva_revision_numero}")

        # Step 4: Validate area_solicitada > 0
        area = payload_in.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Step 5: Calculate M2 cotizacion with IGV
        igv_vigente = self.general_core_service.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")
        igv_porcentaje = Decimal(str(igv_vigente.valor))

        cotizacion = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area,
            tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id),
            igv_porcentaje=igv_porcentaje,
        )

        # Apply min/max clamping on TOTAL (bruto)
        if cotizacion.total < cotizacion.minimo:
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.total > cotizacion.maximo:
            cotizacion.total = cotizacion.maximo

        # Re-derive subtotal and monto_igv from clamped total
        cotizacion.subtotal = (cotizacion.total / (Decimal("1") + igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cotizacion.monto_igv = cotizacion.total - cotizacion.subtotal

        # Step 6: Build domain DTO — reuses proyecto from previous liquidacion
        domain_data = HabilitacionUrbanaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente or previa.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto
                if payload_in.liquidacion_general.denominacion_de_proyecto is not None
                else previa.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=previa.proyecto.nombre_propietario,
                    direccion=previa.proyecto.direccion,
                    distrito_id=str(previa.proyecto.distrito_id) if previa.proyecto.distrito_id else None,
                    urbanizacion=getattr(previa.proyecto, 'urbanizacion', None),
                    entidad_razon_social=previa.proyecto.entidad_razon_social,
                    entidad=EntidadData(
                        tipo_documento=previa.proyecto.entidad_tipo_documento,
                        numero_documento=previa.proyecto.entidad_numero_documento,
                    )
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaHabilitacionUrbanaData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        # Step 7: Delegate to Flujo
        return self.flujo.ejecutar_nueva_revision(
            usuario_id=usuario_id,
            data=domain_data,
            liquidacion_previa=previa,
        )

    def cotizar_proceso(
        self,
        area_solicitada: Decimal,
        tarifa_m2_id: str,
    ) -> CotizacionM2Result:
        """
        Validates area and executes quote calculation with min/max clamping.
        """
        if area_solicitada <= 0:
            raise HttpError(400, "area_solicitada must be greater than 0")

        # Resolve IGV vigente
        igv_vigente = self.general_core_service.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")
        igv_porcentaje = Decimal(str(igv_vigente.valor))

        response = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
            igv_porcentaje=igv_porcentaje,
        )

        # Apply min/max clamping on TOTAL (bruto)
        if response.total < response.minimo:
            response.total = response.minimo
        elif response.maximo is not None and response.total > response.maximo:
            response.total = response.maximo

        # Re-derive subtotal and monto_igv from clamped total
        response.subtotal = (response.total / (Decimal("1") + igv_porcentaje)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        response.monto_igv = response.total - response.subtotal

        return response

    def obtener_tarifas_vigentes_proceso(
        self,
    ) -> tuple[TarifaPorMetroCuadrado, DerechoPorMetroCuadrado]:
        """
        Fetches currently active M2 tariff and derecho for Habilitacion Urbana.
        Returns (tarifa, derecho) tuple.
        """
        tarifa = self.m2_core_service.get_tarifa_m2_vigente(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        )
        derecho = self.m2_core_service.get_derecho_minimo_m2_vigente()
        return (tarifa, derecho)

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
        direccion=None,
    ) -> tuple[List[HabilitacionUrbanaPrimeraRevisionResult], int]:
        """
        Returns paginated HabilitacionUrbanaPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[HabilitacionUrbanaPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_hu_paginated(
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
            direccion=direccion,
        )

        # Build HabilitacionUrbanaPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[HabilitacionUrbanaPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_hu_result(lg))

        return domain_results, total

    def _build_hu_result(self, lg) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to HabilitacionUrbanaPrimeraRevisionResult domain DTO.

        Delegates LiquidacionGeneralResult construction to general_core.build_general_result().
        Only the type-specific fields (habilitacion_urbana, liquidacion_m2) are built here.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
            LiquidacionEspecificaHabilitacionUrbanaResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
            LiquidacionM2Result,
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

        general_result = self.general_core_service.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            codigo_cta=self.general_core_service.get_codigo_cta(lg.tipo_liquidacion),
        )

        # Type-specific: Habilitacion Urbana
        habilitacion_urbana = lg.habilitacion_urbana
        especifica_result = LiquidacionEspecificaHabilitacionUrbanaResult(
            id=str(habilitacion_urbana.id),
            numero=habilitacion_urbana.numero,
        )

        # Get the single M2 record via OneToOne relationship
        m2 = lg.liquidacion_m2.all()[0] if lg.liquidacion_m2.exists() else None

        tipo_result = LiquidacionM2Result(
            id=str(m2.id),
            area_m2=m2.area_m2 if m2 and m2.area_m2 else Decimal("0"),
            costo_por_m2=m2.costo_por_m2 if m2 and m2.costo_por_m2 else Decimal("0"),
            derecho_minimo=m2.derecho_minimo if m2 and m2.derecho_minimo else Decimal("0"),
            derecho_maximo=m2.derecho_maximo if m2 and m2.derecho_maximo else None,
            derecho_aplicado_id=str(m2.derecho.id) if m2 and m2.derecho else "",
            tarifa_aplicada_id=str(m2.tarifa_aplicada.id) if m2 and m2.tarifa_aplicada else "",
        )

        return HabilitacionUrbanaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Returns a single HabilitacionUrbanaPrimeraRevisionResult for HU by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core_service.get_liquidacion_hu_by_id(liquidacion_id)
            return self._build_hu_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

    def recalcular_m2(
        self,
        liquidacion_id: uuid.UUID,
        area_solicitada=None,
        tarifa_m2_id=None,
        liquidacion_general=None,
        liquidacion_tipo=None,
    ):
        """
        PATCH recalculation for Habilitacion Urbana (M2 motor).

        Supports two input formats:
        1. Flat (legacy): area_solicitada + tarifa_m2_id directly
        2. Wrapper (current): liquidacion_general + liquidacion_tipo

        If liquidacion_general is provided, calls general update orchestrator.
        If liquidacion_tipo is provided, delegates to LiquidacionPatchM2Service.
        Both can be provided in one call for atomic update.

        Args:
            liquidacion_id: UUID of the LiquidacionGeneral to recalculate.
            area_solicitada: New area in m2 (flat format, None = preserve current).
            tarifa_m2_id: New tarifa M2 UUID (flat format, None = preserve current).
            liquidacion_general: Optional dict with general fields (wrapper format).
            liquidacion_tipo: Optional dict with tipo fields (wrapper format).

        Returns:
            HabilitacionUrbanaPrimeraRevisionResult with updated values.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
            ConflictError: If estado == PAGADA.
        """
        from django.db import transaction
        from core.exceptions import ConflictError
        from modules.liquidaciones.domain.constants import EstadoLiquidacion
        from modules.liquidaciones.domain.services.core.liquidacion_patch_m2_service import (
            LiquidacionPatchM2Service,
            PatchM2Input,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core_service.get_liquidacion_hu_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

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
            tipo_tarifa = liquidacion_tipo.get("tarifa")
            # Map wrapper field names to flat format
            as_input = tipo_datos.get("area_solicitada", area_solicitada)
            tm2_input = tipo_tarifa.get("tarifa_m2_id") if tipo_tarifa else tarifa_m2_id
        else:
            # Flat format: use params directly
            as_input = area_solicitada
            tm2_input = tarifa_m2_id

        # 4. Execute updates in a single transaction
        patch_service = LiquidacionPatchM2Service()
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
            if as_input is not None or tm2_input is not None:
                patch_input = PatchM2Input(
                    area_solicitada=as_input,
                    tarifa_m2_id=tm2_input,
                )
                patch_service.recalcular(lg, patch_input)

        # 5. Refresh and return built result
        lg.refresh_from_db()
        return self._build_hu_result(lg)

    def cotizar_edicion_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload_in: "CotizarEdicionM2WrapperIn",
    ) -> "CotizacionM2Result":
        """
        Read-only quote for editing an existing Habilitacion Urbana liquidacion.

        Uses historical financial values from LiquidacionGeneral.fecha_registro.
        Does NOT persist any changes.

        Args:
            liquidacion_id: UUID of the existing LiquidacionGeneral.
            payload_in: Typed wrapper with liquidacion_tipo.datos and liquidacion_tipo.tarifa.

        Returns:
            CotizacionM2Result with the calculated quote.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
        """
        from django.core.exceptions import ObjectDoesNotExist
        from modules.liquidaciones.domain.services.core.liquidacion_cotizar_edicion_service import (
            LiquidacionCotizarEdicionM2Service,
            CotizarEdicionM2Input,
        )
        from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
            CotizarEdicionM2WrapperIn,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core_service.get_liquidacion_hu_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

        # 2. Extract fields from typed wrapper
        tipo_datos = payload_in.liquidacion_tipo.datos
        tipo_tarifa = payload_in.liquidacion_tipo.tarifa

        area_solicitada = tipo_datos.area_solicitada
        if area_solicitada is not None and area_solicitada <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        patch_input = CotizarEdicionM2Input(
            area_solicitada=area_solicitada,
            tarifa_m2_id=str(tipo_tarifa.tarifa_m2_id) if tipo_tarifa.tarifa_m2_id else None,
        )

        # 3. Quote (read-only, no DB mutation)
        quote_service = LiquidacionCotizarEdicionM2Service()
        return quote_service.cotizar_edicion(lg, patch_input)

    def crear_edge_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Create an edge (manual) M2 liquidacion for Habilitación Urbana.

        Differences from crear_primera_revision_proceso:
        - modo_calculo = MANUAL (explicit)
        - subtotal_manual is pre-IGV; backend calculates IGV and total
        - No tarifas, no area-based calculation
        - numero_revision is given explicitly (1, 3, or 5)
        - No relation group creation (standalone)
        """
        # Step 1: Validate subtotal_manual > 0
        subtotal_manual = payload_in.subtotal_manual
        if subtotal_manual <= 0:
            raise HttpError(400, "subtotal_manual debe ser mayor a 0")

        # Step 2: Validate area_m2 >= 0 (for traceability)
        area_m2 = payload_in.area_m2
        if area_m2 < 0:
            raise HttpError(400, "area_m2 debe ser mayor o igual a 0")

        # Step 3: Validate numero_revision in {1, 3, 5}
        numero_revision = payload_in.numero_revision
        if numero_revision not in (1, 3, 5):
            raise HttpError(400, "numero_revision debe ser 1, 3 o 5")

        # Step 4: Resolve IGV vigente
        igv_vigente = self.general_core_service.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")

        # Step 5: Build domain data
        gen_data = payload_in.liquidacion_general

        # Step 6: Delegate to Flujo edge
        return self.flujo.ejecutar_edge(
            usuario_id=usuario_id,
            gen_data=gen_data,
            area_m2=area_m2,
            subtotal_manual=subtotal_manual,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            numero_revision=numero_revision,
        )
