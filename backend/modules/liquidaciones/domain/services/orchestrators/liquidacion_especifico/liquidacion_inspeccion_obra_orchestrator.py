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
        general_result = self.general_core.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=None,
            delegados=[],
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
            porcentaje_uit=float(lv.porcentaje_uit) if lv.porcentaje_uit else 0.0,
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
                proyecto=ProyectoData(
                    denominacion=previa.proyecto.denominacion,
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


