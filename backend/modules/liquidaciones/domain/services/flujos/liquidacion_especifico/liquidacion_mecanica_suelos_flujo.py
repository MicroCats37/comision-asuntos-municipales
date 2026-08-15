"""
LiquidacionMecanicaSuelosFlujo — Flujo específico transaccional para Mecánica de Suelos.
"""
from datetime import date
from django.db import transaction
from injector import inject
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.mecanica_suelos_primera_revision_data import (
    MecanicaSuelosPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
    MecanicaSuelosPrimeraRevisionResult,
    LiquidacionEspecificaMecanicaSuelosResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
    LiquidacionM2Result,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionMecanicaSuelosFlujo:
    """
    Transactional flow for creating Mecanica de Suelos (Primera Revisión).
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        m2_core: LiquidacionPorMetroCuadradoCoreService,
    ):
        self.general_core = general_core
        self.m2_core = m2_core

    def ejecutar_primera_revision(
        self,
        usuario_id: int,
        data: MecanicaSuelosPrimeraRevisionData,
    ) -> MecanicaSuelosPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data)

    @transaction.atomic()
    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: MecanicaSuelosPrimeraRevisionData,
    ) -> MecanicaSuelosPrimeraRevisionResult:
        import traceback
        try:
            gen_data = data.liquidacion_general
            esp_data = data.liquidacion_especifica

            # Paso 1: Entidad y Proyecto (General Core)
            entidad = self.general_core.create_entidad(
                tipo_documento=gen_data.proyecto.entidad.tipo_documento,
                numero_documento=gen_data.proyecto.entidad.numero_documento,
            )

            proyecto_data = {
                "denominacion": gen_data.proyecto.denominacion,
                "nombre_propietario": gen_data.proyecto.nombre_propietario,
                "direccion": gen_data.proyecto.direccion,
                "distrito_id": gen_data.proyecto.distrito_id,
                "urbanizacion": None,
                "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
                "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
                "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
            }
            proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

            # Paso 2: Usar cotizacion pre-clamped del Orchestrator (clamping vive en Orchestrator, no aquí)
            cotizacion = data.cotizacion

            # Obtener IGV y UIT vigentes para asignar FKs
            igv_vigente = self.general_core.get_igv_vigente()
            uit_vigente = self.general_core.get_uit_vigente()

            # Paso 3: LiquidacionGeneral (General Core)
            from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
            liquidacion_general = self.general_core.create_liquidacion_general(
                municipalidad_id=gen_data.municipalidad_id,
                expediente=gen_data.expediente,
                observacion=gen_data.observacion,
                proyecto=proyecto,
                tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.MECANICA_SUELOS),
                numero_revision=1,
            )
            liquidacion_general.sub_total = Decimal(str(cotizacion.subtotal))
            liquidacion_general.total = Decimal(str(cotizacion.total))
            liquidacion_general.igv_id = igv_vigente
            liquidacion_general.uit_id = uit_vigente
            liquidacion_general.usuario_creador_id = usuario_id
            liquidacion_general.save()

            # Paso 4: Crear LiquidacionPorMetroCuadrado (M2 Core)
            derecho = self.m2_core.get_derecho_minimo_m2_vigente()
            tarifa = self.m2_core.get_tarifa_m2_vigente(TipoLiquidacion.MECANICA_SUELOS)
            liquidacion_m2 = self.m2_core.create_liquidacion_por_metro_cuadrado(
                liquidacion_general=liquidacion_general,
                area_solicitada=float(esp_data.datos.area_solicitada),
                tarifa_aplicada=tarifa,
                derecho_aplicado=derecho,
                subtotal=liquidacion_general.sub_total,
                total=liquidacion_general.total,
            )

            # Paso 5: Crear el Wrapper Específico de Mecánica de Suelos (ORM Directo)
            liquidacion_especifica = LiquidacionMecanicaSuelos.objects.create(
                liquidacion=liquidacion_general
            )

            # Paso 6: Construir el Result 100% tipado con Pydantic
            # Delegates common ORM→Result mapping to core
            general_result = self.general_core.build_general_result(
                liquidacion_general=liquidacion_general,
                usuario_id=usuario_id,
                fecha_registro=str(liquidacion_general.fecha_registro) if liquidacion_general.fecha_registro else "",
            )

            tipo_result = LiquidacionM2Result(
                id=str(liquidacion_m2.id),
                area_m2=float(liquidacion_m2.area_m2),
                costo_por_m2=float(liquidacion_m2.costo_por_m2),
                derecho_minimo=float(liquidacion_m2.derecho_minimo),
                derecho_maximo=float(liquidacion_m2.derecho_maximo) if liquidacion_m2.derecho_maximo else None,
                derecho_aplicado_id=str(derecho.id),
                tarifa_aplicada_id=str(liquidacion_m2.tarifa_aplicada_id),
            )

            especifica_result = LiquidacionEspecificaMecanicaSuelosResult(
                id=str(liquidacion_especifica.id),
                numero=liquidacion_especifica.numero,
            )

            return MecanicaSuelosPrimeraRevisionResult(
                liquidacion_general=general_result,
                liquidacion_tipo=tipo_result,
                liquidacion_especifica=especifica_result,
            )
        except Exception as e:
            print("==== EXACT ERROR ====")
            traceback.print_exc()
            raise e
