"""
Orquestador de Inspeccion de Obra.
Mapea los Schemas de Presentacion (Input) hacia los DTOs de Dominio (Data).
Ejecuta el Flujo de forma sincrona.
"""
from injector import inject

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraPrimeraRevisionData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionTipoVisitasData,
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
        visitas_data = LiquidacionTipoVisitasData(
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
        Orquesta el calculo de cotizacion para Inspeccion de Obra delegando en el Core de Visitas.
        """
        tarifa = self.visitas_core.get_tarifa_por_id(tarifa_id)
        
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise ValueError("No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise ValueError("No hay IGV vigente configurado.")

        subtotal = self.visitas_core.calcular_subtotal_visitas(
            cantidad_visitas=cantidad_visitas,
            tarifa=tarifa,
            uit_vigente=uit_vigente,
        )

        igv_valor = float(igv_vigente.valor)
        costo_por_visita = float(tarifa.porcentaje_uit) * float(uit_vigente.valor)
        total = float(subtotal) * (1 + igv_valor)

        return CotizacionVisitasResult(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            costo_por_visita=costo_por_visita,
            tarifa_id=str(tarifa.id),
            monto_bruto=float(subtotal),
            subtotal=float(subtotal),
            total=total,
            uit={"id": str(uit_vigente.id), "valor": float(uit_vigente.valor)},
            igv={"id": str(igv_vigente.id), "valor": float(igv_vigente.valor)},
        )
