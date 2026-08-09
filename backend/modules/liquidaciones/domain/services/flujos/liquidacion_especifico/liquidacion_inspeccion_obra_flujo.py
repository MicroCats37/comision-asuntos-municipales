"""
Flujo para Inspección de Obra (Transaccional).
"""
from django.db import transaction
from injector import inject
import uuid

from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
    LiquidacionEspecificaInspeccionObraResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
    LiquidacionVisitasResult,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)


class LiquidacionInspeccionObraFlujo:
    """
    Flujo transaccional que orquesta la creación completa de Inspección de Obra.
    Usa el Core de General y el Core de Visitas.
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        visitas_core: LiquidacionPorCategoriaVisitasCoreService,
    ):
        self.general_core = general_core
        self.visitas_core = visitas_core

    @transaction.atomic()
    def ejecutar_primera_revision(
        self,
        usuario_id: int,
        data: InspeccionObraPrimeraRevisionData,
    ) -> InspeccionObraPrimeraRevisionResult:
        # 1. Traer tarifa, UIT y calcular (validation moved to Orchestrator)
        tarifa = self.visitas_core.get_tarifa_por_id(data.liquidacion_especifica.tarifa.tarifa_visitas_id)

        uit_vigente = self.general_core.get_uit_vigente()

        subtotal = self.visitas_core.calcular_subtotal_visitas(
            cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
            tarifa=tarifa,
            uit_vigente=uit_vigente,
        )

        igv_vigente = self.general_core.get_igv_vigente()

        # 2. Crear Entidad y Proyecto
        gen_data = data.liquidacion_general
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

        # 3. Crear General
        from modules.liquidaciones.domain.constants import TipoLiquidacion
        
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA,
            numero_revision=1,
        )
        
        # Aplicar totales con IGV manualmente, y asignar FKs de impuestos
        liquidacion_general.sub_total = subtotal
        liquidacion_general.total = subtotal * (1 + igv_vigente.valor)
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id
        liquidacion_general.save()

        # 3. Crear Tipo: LiquidacionPorCategoriaVisitas
        liquidacion_visitas = self.visitas_core.crear_liquidacion_tipo_visitas(
            liquidacion_general=liquidacion_general,
            data=data.liquidacion_especifica,
        )

        # 4. Crear Específico: LiquidacionInspeccionObra
        liquidacion_io = LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
        )

        # 5. Mapear a Result puro (Cero dicts)
        from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
            ProyectoResult, EntidadResult, UsuarioCreadorResult
        )

        entidad_result = None
        if entidad:
            entidad_result = EntidadResult(
                razon_social=proyecto.entidad_razon_social,
                tipo_documento=entidad.tipo_documento,
                numero_documento=entidad.numero_documento,
            )

        proyecto_result = ProyectoResult(
            id=str(proyecto.id),
            denominacion=proyecto.denominacion,
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            distrito_id=str(proyecto.distrito_id),
            entidad=entidad_result,
        )

        general_result = LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            municipalidad_id=str(liquidacion_general.municipalidad_id),
            usuario_creador=UsuarioCreadorResult(id=str(usuario_id)),
            fecha_registro=str(liquidacion_general.fecha_registro) if liquidacion_general.fecha_registro else "",
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            igv_id=str(liquidacion_general.igv_id.id) if liquidacion_general.igv_id else None,
            uit_id=str(liquidacion_general.uit_id.id) if liquidacion_general.uit_id else None,
            proyecto=proyecto_result,
        )

        tipo_result = LiquidacionVisitasResult(
            id=str(liquidacion_visitas.id),
            cantidad_visitas=liquidacion_visitas.cantidad_visitas,
            porcentaje_uit=float(liquidacion_visitas.porcentaje_uit),
            categoria=liquidacion_visitas.categoria,
            tarifa_aplicada_id=str(liquidacion_visitas.tarifa_aplicada_id),
        )

        especifico_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(liquidacion_io.id),
            numero=liquidacion_io.numero,
        )

        return InspeccionObraPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_tipo=tipo_result,
            liquidacion_especifica=especifico_result,
        )
