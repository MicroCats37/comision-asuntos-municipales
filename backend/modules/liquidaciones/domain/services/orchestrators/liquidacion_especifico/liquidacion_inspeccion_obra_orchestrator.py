"""
Orquestador de Inspeccion de Obra.
Mapea los Schemas de Presentacion (Input) hacia los DTOs de Dominio (Data).
Ejecuta el Flujo de forma sincrona.
"""
import uuid
from django.core.exceptions import ObjectDoesNotExist
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraPrimeraRevisionData,
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
    ):
        self.flujo = flujo
        self.visitas_core = visitas_core
        self.general_core = general_core

    def crear_primera_revision_proceso(
        self, usuario_id: int, payload_in: LiquidacionInspeccionObraInput
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Mapea el schema de Presentacion a DTOs de Dominio puros.
        """
        # Pre-validation: ensure UIT and IGV are configured (moved from Flujo)
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(404, "No hay IGV vigente configurado.")

        # Pre-validation: ensure tariff exists
        tarifa_visitas_id = str(payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = self.visitas_core.get_tarifa_por_id(tarifa_visitas_id)
        if not tarifa:
            raise HttpError(404, f"No se encontró tarifa válida para ID {tarifa_visitas_id}")

        # Mapeo General
        gen_in = payload_in.liquidacion_general
        proy_in = gen_in.proyecto

        entidad_data = EntidadData(
            tipo_documento=proy_in.entidad.tipo_documento,
            numero_documento=proy_in.entidad.numero_documento,
        )

        proyecto_data = ProyectoData(
            denominacion=proy_in.denominacion,
            nombre_propietario=proy_in.nombre_propietario,
            direccion=proy_in.direccion,
            distrito_id=str(proy_in.distrito_id),
            entidad_razon_social=proy_in.entidad.razon_social,
            entidad=entidad_data,
        )

        general_data = LiquidacionGeneralData(
            municipalidad_id=str(gen_in.municipalidad_id),
            expediente=gen_in.expediente,
            observacion=gen_in.observacion,
            proyecto=proyecto_data,
        )

        # Mapeo Especifico (Visitas)
        visitas_in = payload_in.liquidacion_especifica
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=visitas_in.datos.cantidad_visitas,
                categoria=visitas_in.datos.categoria,
            ),
            tarifa=TarifaVisitas(
                tarifa_visitas_id=str(visitas_in.tarifa.tarifa_visitas_id)
            ),
        )

        # Wrapper Final DTO
        domain_data = InspeccionObraPrimeraRevisionData(
            liquidacion_general=general_data,
            liquidacion_especifica=visitas_data,
        )

        # Ejecucion transaccional en hilo sincronico
        return self.flujo.ejecutar_primera_revision(usuario_id, domain_data)

    def cotizar_proceso(
        self,
        cantidad_visitas: int,
        categoria: str,
        tarifa_id: str,
    ) -> CotizacionVisitasResult:
        """
        Orchestrates the quote calculation for Inspeccion de Obra.
        Applies clamping via UIT-based bounds since Visitas has no derecho model.
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

        # Apply min/max clamping using UIT-based bounds (Visitas has no derecho model)
        uit_valor = float(uit_vigente.valor)
        minimo_uit = uit_valor * 1  # Minimum 1 UIT
        maximo_uit = uit_valor * 100  # Maximum 100 UIT

        clamped_subtotal = result.subtotal
        if clamped_subtotal < minimo_uit:
            clamped_subtotal = minimo_uit
        elif clamped_subtotal > maximo_uit:
            clamped_subtotal = maximo_uit

        # Recalculate total with clamped subtotal
        clamped_total = clamped_subtotal * (1 + float(igv_vigente.valor))

        # Return a new result with clamped values (Pydantic models are immutable)
        return CotizacionVisitasResult(
            cantidad_visitas=result.cantidad_visitas,
            categoria=result.categoria,
            costo_por_visita=result.costo_por_visita,
            tarifa_id=result.tarifa_id,
            monto_bruto=result.monto_bruto,
            subtotal=clamped_subtotal,
            total=clamped_total,
            uit=result.uit,
            igv=result.igv,
        )

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

    def listar_liquidaciones(self, page: int, page_size: int) -> tuple:
        """
        Returns paginated liquidaciones for Inspección de Obra type.
        Delegates to general_core_service with INSPECCION_OBRA type.
        Returns (queryset, total_count).
        """
        return self.general_core.list_liquidaciones_io_paginated(
            page=page,
            page_size=page_size,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID):
        """
        Returns a single LiquidacionGeneral for Inspección de Obra by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            return self.general_core.get_liquidacion_io_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")
