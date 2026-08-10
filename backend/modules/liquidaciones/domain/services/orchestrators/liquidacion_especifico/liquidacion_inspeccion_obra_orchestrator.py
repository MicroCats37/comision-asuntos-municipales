"""
Orquestador de Inspeccion de Obra.
Mapea los Schemas de Presentacion (Input) hacia los DTOs de Dominio (Data).
Ejecuta el Flujo de forma sincrona.
"""
import uuid
from typing import List
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

    def listar_liquidaciones(
        self, page: int, page_size: int
    ) -> tuple:
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
        )

        # Build InspeccionObraPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[InspeccionObraPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_io_result(lg))

        return domain_results, total

    def _build_io_result(self, lg) -> InspeccionObraPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to InspeccionObraPrimeraRevisionResult domain DTO.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
            LiquidacionEspecificaInspeccionObraResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
            LiquidacionGeneralResult,
            EntidadResult,
            ProyectoResult,
            UsuarioCreadorResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
            LiquidacionVisitasResult,
        )

        proyecto = lg.proyecto
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        if entidad is None:
            ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
            ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
            ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None
        else:
            ent_tipo = entidad.tipo_documento
            ent_numero = entidad.numero_documento
            ent_razon = entidad.razon_social

        general_result = LiquidacionGeneralResult(
            id=str(lg.id),
            municipalidad_id=str(lg.municipalidad_id),
            usuario_creador=UsuarioCreadorResult(
                id=str(lg.usuario_creador.id) if lg.usuario_creador else "00000000-0000-0000-0000-000000000000",
            ),
            fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
            expediente=lg.expediente or "",
            observacion=lg.observacion,
            numero_revision=lg.numero_revision,
            sub_total=float(lg.sub_total) if lg.sub_total else 0.0,
            total=float(lg.total) if lg.total else 0.0,
            igv_id=str(lg.igv_id.id) if lg.igv_id else None,
            uit_id=str(lg.uit_id.id) if lg.uit_id else None,
            proyecto=ProyectoResult(
                id=str(proyecto.id),
                denominacion=proyecto.denominacion,
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito_id=str(proyecto.distrito_id),
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
        )

        io = lg.inspeccion_obra
        especifica_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(io.id),
            numero=io.numero,
        )

        lv = lg.liquidacion_visitas.first()
        tipo_result = LiquidacionVisitasResult(
            id=str(lv.id),
            cantidad_visitas=lv.cantidad_visitas,
            porcentaje_uit=float(lv.porcentaje_uit) if lv.porcentaje_uit else 0.0,
            categoria=lv.categoria or "",
            tarifa_aplicada_id=str(lv.tarifa_aplicada_id),
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


