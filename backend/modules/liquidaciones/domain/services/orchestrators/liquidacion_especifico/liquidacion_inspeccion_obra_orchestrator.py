"""
Orquestador de Inspeccion de Obra.
Mapea los Schemas de Presentacion (Input) hacia los DTOs de Dominio (Data).
Ejecuta el Flujo de forma sincrona.
"""
import uuid
from typing import List, Optional
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraNuevaRevisionInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraNuevaRevisionData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionCategoriaVisitasData,
    DatosVisitas,
    TarifaVisitas,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
    ProyectoData,
    EntidadData,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_inspeccion_obra_flujo import (
    LiquidacionInspeccionObraFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionVisitasResult,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)

class LiquidacionInspeccionObraOrchestrator:
    @inject
    def __init__(
        self,
        flujo: LiquidacionInspeccionObraFlujo,
        visitas_core: LiquidacionPorCategoriaVisitasCoreService,
        general_core: LiquidacionGeneralCoreService,
        general_orchestrator: LiquidacionGeneralOrchestrator,
    ):
        self.flujo = flujo
        self.visitas_core = visitas_core
        self.general_core = general_core
        self.general_orchestrator = general_orchestrator

    def cotizar_proceso(
        self,
        cantidad_visitas: int,
        categoria: str,
        tarifa_id: str,
    ) -> CotizacionVisitasResult:
        """
        Orchestrates the quote calculation for Inspeccion de Obra.

        El cálculo es: cantidad_visitas × (porcentaje_uit × UIT) + IGV.
        NO aplica clamping de UIT (a diferencia del motor PorcentajeObra) —
        Visitas se cobra por visita según la categoría, sin mínimo de 1 UIT.
        Debe coincidir EXACTAMENTE con la creación (ejecutar_primera_revision_desde_previa).
        """
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(404, "No hay IGV vigente configurado.")

        result = self.visitas_core.calcular_cotizacion_visitas(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_visitas_id=tarifa_id,
            uit_vigente=uit_vigente,
            igv_vigente=igv_vigente,
        )

        if result is None:
            raise HttpError(404, f"No se encontró una tarifa válida para ID {tarifa_id}")

        return result

    def obtener_tarifas_vigentes_proceso(self) -> tuple:
        """
        Orchestrates fetching vigente tarifas and UIT.
        Returns (tarifas, uit_vigente) tuple.
        """
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        tarifas = self.visitas_core.get_tarifas_vigentes()
        return (tarifas, uit_vigente)

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
    ) -> tuple[List[InspeccionObraPrimeraRevisionResult], int]:
        """
        Returns paginated InspeccionObraPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[InspeccionObraPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core.list_liquidaciones_io_paginated(
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

        # Build InspeccionObraPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[InspeccionObraPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_io_result(lg))

        return domain_results, total

    def _build_io_result(self, lg) -> InspeccionObraPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to InspeccionObraPrimeraRevisionResult domain DTO.

        Delegates LiquidacionGeneralResult construction to general_core.build_general_result().
        Only the type-specific fields (inspeccion_obra, liquidacion_visitas) are built here.
        IO does not use contacto_result or delegados.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
            LiquidacionEspecificaInspeccionObraResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
            LiquidacionVisitasResult,
        )
        from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_inspeccion_obra_flujo import (
            LiquidacionInspeccionObraFlujo,
        )

        # Delegate general result construction to core (NO more duplicate inline mapping)
        # IO does not use contacto_result or delegados — pass empty lists
        usuario_id = lg.usuario_creador.id if lg.usuario_creador else 0
        revisiones_previas = self.general_core.build_revisiones_previas_result(lg)
        general_result = self.general_core.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=None,
            delegados=[],
            codigo_cta=self.general_core.get_codigo_cta(lg.tipo_liquidacion),
            revisiones_previas=revisiones_previas,
        )

        # Type-specific: Inspeccion Obra
        io = lg.inspeccion_obra
        especifica_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(io.id),
            numero=io.numero,
        )

        lv = lg.liquidacion_visitas.first()
        tipo_result = LiquidacionVisitasResult(
            id=str(lv.id),
            cantidad_visitas=lv.cantidad_visitas,
            porcentaje_uit=lv.porcentaje_uit if lv.porcentaje_uit else Decimal("0"),
            categoria=lv.categoria or "",
            tarifa_aplicada_id=str(lv.tarifa_aplicada_id),
            inspectores=LiquidacionInspeccionObraFlujo._build_inspectores_result(lv),
        )

        return InspeccionObraPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> InspeccionObraPrimeraRevisionResult:
        """
        Returns a single InspeccionObraPrimeraRevisionResult for Inspección de Obra by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
            return self._build_io_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

    def crear_primera_revision_desde_previa_proceso(
        self,
        usuario_id: int,
        payload_in: LiquidacionInspeccionObraNuevaRevisionInput,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision heredando proyecto/municipalidad/entidad
        de una liquidación previa (Edificación o Habilitación Urbana).

        Validations:
        - liquidacion_previa_id existe y es EDIFICACION o HABILITACION_URBANA
        - tariff exists
        - UIT and IGV are configured
        """
        from modules.liquidaciones.domain.constants import TipoLiquidacion

        # Step 1: Validate liquidacion_previa exists and is EDIFICACION or HABILITACION_URBANA
        try:
            previa = self.general_core.get_liquidacion_previa_para_io(
                payload_in.liquidacion_previa_id
            )
        except ObjectDoesNotExist:
            raise HttpError(404, f"Liquidación previa {payload_in.liquidacion_previa_id} no encontrada")

        tipo_previo = previa.tipo_liquidacion.codigo
        if tipo_previo not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            raise HttpError(
                400,
                f"La liquidación previa debe ser Edificación o Habilitación Urbana. "
                f"Se proporcionó: {tipo_previo}"
            )

        # Step 2: Pre-validate UIT and IGV
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(404, "No hay IGV vigente configurado.")

        # Step 3: Pre-validate tariff
        tarifa_visitas_id = str(payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = self.visitas_core.get_tarifa_por_id(tarifa_visitas_id)
        if not tarifa:
            raise HttpError(404, f"No se encontró tarifa válida para ID {tarifa_visitas_id}")

        # Step 4: Pre-validate inspector exists
        from modules.liquidaciones.domain.models.inspector import Inspector
        try:
            inspector = Inspector.objects.get(id=payload_in.liquidacion_especifica.inspector_id)
        except ObjectDoesNotExist:
            raise HttpError(404, f"No se encontró inspector con ID {payload_in.liquidacion_especifica.inspector_id}")

        # Step 5: Build domain data inheriting from previa
        # Entidad and Proyecto are reused from previa (not created new)
        gen_data = payload_in.liquidacion_especifica
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=gen_data.datos.cantidad_visitas,
                categoria=gen_data.datos.categoria,
            ),
            tarifa=TarifaVisitas(
                tarifa_visitas_id=str(gen_data.tarifa.tarifa_visitas_id)
            ),
        )

        domain_data = InspeccionObraNuevaRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=previa.expediente,
                observacion=previa.observacion,
                retencion=previa.retencion,
                denominacion_de_proyecto=previa.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=previa.proyecto.nombre_propietario,
                    direccion=previa.proyecto.direccion,
                    distrito_id=str(previa.proyecto.distrito_id),
                    entidad_razon_social=getattr(previa.proyecto, 'entidad_razon_social', None),
                    entidad=EntidadData(
                        tipo_documento=getattr(previa.proyecto, 'entidad_tipo_documento', None) or "",
                        numero_documento=getattr(previa.proyecto, 'entidad_numero_documento', None) or "",
                    ),
                ),
            ),
            liquidacion_especifica=visitas_data,
            inspector_id=payload_in.liquidacion_especifica.inspector_id,
        )

        # Step 6: Execute in flujo
        return self.flujo.ejecutar_primera_revision_desde_previa(
            usuario_id=usuario_id,
            data=domain_data,
            liquidacion_previa=previa,
            inspector=inspector,
        )

    def recalcular_visitas(
        self,
        liquidacion_id: uuid.UUID,
        cantidad_visitas=None,
        categoria=None,
        tarifa_visitas_id=None,
        liquidacion_general=None,
        liquidacion_tipo=None,
    ):
        """
        PATCH recalculation for Inspeccion de Obra (Visitas motor).

        Supports two input formats:
        1. Flat (legacy): cantidad_visitas + categoria + tarifa_visitas_id directly
        2. Wrapper (current): liquidacion_general + liquidacion_tipo

        If liquidacion_general is provided, calls general update orchestrator.
        If liquidacion_tipo is provided, delegates to LiquidacionPatchVisitasService.
        Both can be provided in one call for atomic update.

        Args:
            liquidacion_id: UUID of the LiquidacionGeneral to recalculate.
            cantidad_visitas: New cantidad_visitas (flat format, None = preserve current).
            categoria: New categoria string (flat format, None = preserve current).
            tarifa_visitas_id: New tarifa UUID (flat format, None = preserve current).
            liquidacion_general: Optional dict with general fields (wrapper format).
            liquidacion_tipo: Optional dict with tipo fields (wrapper format).

        Returns:
            InspeccionObraPrimeraRevisionResult with updated values.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
            ConflictError: If estado == PAGADA.
        """
        from django.db import transaction
        from core.exceptions import ConflictError
        from modules.liquidaciones.domain.constants import EstadoLiquidacion
        from modules.liquidaciones.domain.services.core.liquidacion_patch_visitas_service import (
            LiquidacionPatchVisitasService,
            PatchVisitasInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
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
            tipo_tarifa = liquidacion_tipo.get("tarifa")
            # Map wrapper field names to flat format
            cv_input = tipo_datos.get("cantidad_visitas", cantidad_visitas)
            cat_input = tipo_datos.get("categoria", categoria)
            tv_input = tipo_tarifa.get("tarifa_visitas_id") if tipo_tarifa else tarifa_visitas_id
            inspector_operacion_id = liquidacion_tipo.get("inspector_operacion_id")
        else:
            # Flat format: use params directly
            cv_input = cantidad_visitas
            cat_input = categoria
            tv_input = tarifa_visitas_id
            inspector_operacion_id = None

        # 4. Execute updates in a single transaction
        patch_service = LiquidacionPatchVisitasService()
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
            if cv_input is not None or cat_input is not None or tv_input is not None:
                patch_input = PatchVisitasInput(
                    cantidad_visitas=cv_input,
                    categoria=cat_input,
                    tarifa_visitas_id=tv_input,
                )
                patch_service.recalcular(lg, patch_input)

            # 4c. Update inspector if inspector_operacion_id is provided
            if inspector_operacion_id is not None:
                from modules.liquidaciones.domain.models.inspector import (
                    InspectorOperacion,
                    LiquidacionInspector,
                )
                # Get the liquidacion_visitas (liquidacion tipo)
                lv = lg.liquidacion_visitas.first()
                if lv is not None:
                    # Delete existing LiquidacionInspector for this liquidacion
                    LiquidacionInspector.objects.filter(liquidacion=lv).delete()
                    # Find the InspectorOperacion
                    try:
                        inspector_operacion = InspectorOperacion.objects.get(
                            id=inspector_operacion_id
                        )
                    except ObjectDoesNotExist:
                        raise HttpError(
                            404,
                            f"No se encontró InspectorOperacion con ID {inspector_operacion_id}",
                        )
                    # Create new LiquidacionInspector
                    LiquidacionInspector.objects.create(
                        liquidacion=lv,
                        inspector=inspector_operacion.inspector,
                        inspector_operacion=inspector_operacion,
                        especialidad_revision=inspector_operacion.especialidad_revision,
                    )

        # 5. Refresh and return built result
        lg.refresh_from_db()
        return self._build_io_result(lg)

    def cotizar_edicion_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload_in: "CotizarEdicionVisitasWrapperIn",
    ) -> "CotizacionVisitasResult":
        """
        Read-only quote for editing an existing Inspeccion de Obra liquidacion.

        Uses historical financial values from LiquidacionGeneral.fecha_registro.
        Does NOT persist any changes.

        Args:
            liquidacion_id: UUID of the existing LiquidacionGeneral.
            payload_in: Typed wrapper with liquidacion_tipo.datos and liquidacion_tipo.tarifa.

        Returns:
            CotizacionVisitasResult with the calculated quote.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
        """
        from django.core.exceptions import ObjectDoesNotExist
        from modules.liquidaciones.domain.services.core.liquidacion_cotizar_edicion_service import (
            LiquidacionCotizarEdicionVisitasService,
            CotizarEdicionVisitasInput,
        )
        from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
            CotizarEdicionVisitasWrapperIn,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

        # 2. Extract fields from typed wrapper
        tipo_datos = payload_in.liquidacion_tipo.datos
        tipo_tarifa = payload_in.liquidacion_tipo.tarifa

        cantidad_visitas = tipo_datos.cantidad_visitas
        if cantidad_visitas is not None and cantidad_visitas < 1:
            raise HttpError(400, "cantidad_visitas debe ser >= 1")

        patch_input = CotizarEdicionVisitasInput(
            cantidad_visitas=cantidad_visitas,
            categoria=tipo_datos.categoria,
            tarifa_visitas_id=str(tipo_tarifa.tarifa_visitas_id) if tipo_tarifa.tarifa_visitas_id else None,
        )

        # 3. Quote (read-only, no DB mutation)
        quote_service = LiquidacionCotizarEdicionVisitasService()
        return quote_service.cotizar_edicion(lg, patch_input)
