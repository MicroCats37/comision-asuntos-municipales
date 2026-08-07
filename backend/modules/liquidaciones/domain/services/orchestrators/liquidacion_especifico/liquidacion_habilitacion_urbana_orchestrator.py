"""
LiquidacionHabilitacionUrbanaOrchestrator — sync facade for Habilitacion Urbana.

Thin sync facade. Validates input and delegates to Core/Flujo for calculation.
"""
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_habilitacion_urbana_flujo import (
    LiquidacionHabilitacionUrbanaFlujo,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.habilitacion_urbana_primera_revision_data import (
    HabilitacionUrbanaPrimeraRevisionData,
    LiquidacionEspecificaHabilitacionUrbanaData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
    HabilitacionUrbanaPrimeraRevisionResult,
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
        flujo: LiquidacionHabilitacionUrbanaFlujo,
    ):
        self.m2_core_service = m2_core_service
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

        # Mapear Presentation Schema -> Domain DTO
        domain_data = HabilitacionUrbanaPrimeraRevisionData(
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
            liquidacion_especifica=LiquidacionEspecificaHabilitacionUrbanaData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            )
        )

        response = self.flujo.ejecutar_primera_revision(usuario_id=usuario_id, data=domain_data)
        
        return response

    def cotizar_proceso(
        self,
        area_solicitada: float,
        tarifa_m2_id: str,
    ) -> CotizacionM2Result:
        """
        Validates area and executes quote calculation.
        """
        if area_solicitada <= 0:
            raise HttpError(400, "area_solicitada must be greater than 0")

        response = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
        )

        return response
