"""
LiquidacionMecanicaSuelosOrchestrator — sync facade for Mecanica de Suelos.

Thin sync facade. Validates input and delegates to Core/Flujo for calculation.
"""
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_mecanica_suelos_flujo import (
    LiquidacionMecanicaSuelosFlujo,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.mecanica_suelos_primera_revision_data import (
    MecanicaSuelosPrimeraRevisionData,
    LiquidacionEspecificaMecanicaSuelosData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
    MecanicaSuelosPrimeraRevisionResult,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
    ProyectoData,
    EntidadData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)


class LiquidacionMecanicaSuelosOrchestrator:
    """
    Sync facade for Mecanica de Suelos liquidacion.

    Responsibilities:
    - Input validation (area_solicitada > 0)
    - Delegates to M2 Core service for calculation
    """

    @inject
    def __init__(
        self,
        m2_core_service: LiquidacionPorMetroCuadradoCoreService,
        flujo: LiquidacionMecanicaSuelosFlujo,
    ):
        self.m2_core_service = m2_core_service
        self.flujo = flujo

    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in: LiquidacionMecanicaSuelosInput,
    ) -> MecanicaSuelosPrimeraRevisionResult:
        """
        Valida y orquesta la creacion de Mecanica de Suelos (Primera Revision).
        """
        area = payload_in.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Calculate and clamp M2 cotizacion (same pattern as cotizar_proceso)
        cotizacion = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            area_solicitada=area,
            tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id),
        )

        # Apply min/max clamping (Orchestrator is the ONLY place this logic lives)
        if cotizacion.subtotal < cotizacion.minimo:
            cotizacion.subtotal = cotizacion.minimo
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.subtotal > cotizacion.maximo:
            cotizacion.subtotal = cotizacion.maximo
            cotizacion.total = cotizacion.maximo

        # Mapear Presentation Schema -> Domain DTO (with pre-clamped cotizacion)
        domain_data = MecanicaSuelosPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                proyecto=ProyectoData(
                    denominacion=payload_in.liquidacion_general.proyecto.denominacion,
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id),
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    )
                )
            ),
            liquidacion_especifica=LiquidacionEspecificaMecanicaSuelosData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        response = self.flujo.ejecutar_primera_revision(usuario_id=usuario_id, data=domain_data)
        
        return response

    def cotizar_proceso(
        self,
        area_solicitada: float,
        tarifa_m2_id: str,
    ) -> CotizacionM2Result:
        """
        Validates area and executes quote calculation with min/max clamping.
        """
        if area_solicitada <= 0:
            raise HttpError(400, "area_solicitada must be greater than 0")

        response = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
        )

        # Apply min/max clamping after getting raw data from Core
        if response.subtotal < response.minimo:
            response.subtotal = response.minimo
            response.total = response.minimo
        elif response.maximo is not None and response.subtotal > response.maximo:
            response.subtotal = response.maximo
            response.total = response.maximo

        return response

    def obtener_tarifas_vigentes_proceso(
        self,
    ) -> tuple[TarifaPorMetroCuadrado, DerechoPorMetroCuadrado]:
        """
        Fetches currently active M2 tariff and derecho for Mecanica de Suelos.
        Returns (tarifa, derecho) tuple.
        """
        tarifa = self.m2_core_service.get_tarifa_m2_vigente(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
        )
        derecho = self.m2_core_service.get_derecho_minimo_m2_vigente()
        return (tarifa, derecho)
