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
    InspeccionObraNuevaRevisionData,
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
from modules.liquidaciones.domain.constants import TipoLiquidacion


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
    def ejecutar_primera_revision_desde_previa(
        self,
        usuario_id: int,
        data: InspeccionObraNuevaRevisionData,
        liquidacion_previa,
        inspector,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision heredando proyecto/municipalidad/entidad
        de una liquidación previa (Edificación o Habilitación Urbana).

        Diferencias respecto a ejecutar_primera_revision:
        - Entidad y Proyecto se HEREDAN de la liquidación previa (no se crean nuevos)
        - numero_revision = 1 (siempre)
        - Se crea LiquidacionInspector para asociar el inspector
        - No se usa upsert_contacto (el contacto viene en el dominio, no se pide en el input)
        """
        # 1. Traer tarifa, UIT y calcular
        tarifa = self.visitas_core.get_tarifa_por_id(data.liquidacion_especifica.tarifa.tarifa_visitas_id)
        uit_vigente = self.general_core.get_uit_vigente()
        igv_vigente = self.general_core.get_igv_vigente()

        subtotal = self.visitas_core.calcular_subtotal_visitas(
            cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
            tarifa=tarifa,
            uit_vigente=uit_vigente,
        )

        # 2. Entidad y Proyecto ya existen — obtenerlos de la liquidación previa
        proyecto = liquidacion_previa.proyecto
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # 3. Crear LiquidacionGeneral con tipo_liquidacion=INSPECCION_OBRA y numero_revision=1
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(liquidacion_previa.municipalidad_id),
            expediente=liquidacion_previa.expediente,
            observacion=liquidacion_previa.observacion,
            retencion=liquidacion_previa.retencion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.INSPECCION_OBRA),
            numero_revision=1,
        )

        # Aplicar totales con IGV y asignar FKs de impuestos
        liquidacion_general.sub_total = subtotal
        liquidacion_general.total = subtotal * (1 + igv_vigente.valor)
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id
        liquidacion_general.save()

        # 4. Crear Tipo: LiquidacionPorCategoriaVisitas
        liquidacion_visitas = self.visitas_core.crear_liquidacion_tipo_visitas(
            liquidacion_general=liquidacion_general,
            data=data.liquidacion_especifica,
        )

        # 5. Crear Específico: LiquidacionInspeccionObra
        liquidacion_io = LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
        )

        # 6. Crear LiquidacionInspector (asocia el inspector a la IO)
        # La especialidad_revision se resuelve desde la operación del inspector
        # para el TIPO DE LA LIQUIDACIÓN PREVIA (EDIFICACION/HABILITACION_URBANA).
        # Los inspectores NO se registran con tipo INSPECCION_OBRA — se registran
        # con el tipo del trámite que pueden revisar (el de la previa).
        from modules.liquidaciones.domain.models.inspector import InspectorOperacion
        from ninja.errors import HttpError

        tipo_previa = liquidacion_previa.tipo_liquidacion.codigo
        especialidad_revision = (
            InspectorOperacion.objects
            .filter(
                inspector=inspector,
                tipo_liquidacion__codigo=tipo_previa,
            )
            .values_list("especialidad_revision_id", flat=True)
            .first()
        )
        if not especialidad_revision:
            raise HttpError(
                400,
                f"El inspector no tiene una operación vigente con especialidad "
                f"para el tipo '{tipo_previa}' de la liquidación previa.",
            )
        LiquidacionInspector.objects.create(
            liquidacion=liquidacion_visitas,
            inspector=inspector,
            especialidad_revision_id=especialidad_revision,
        )

        # 7. Mapear a Result puro (reutiliza la lógica de mapeo de ejecutar_primera_revision)
        return self._build_result_from_orm(
            liquidacion_general=liquidacion_general,
            liquidacion_io=liquidacion_io,
            liquidacion_visitas=liquidacion_visitas,
            proyecto=proyecto,
            entidad=entidad,
            usuario_id=usuario_id,
        )

    def _build_result_from_orm(
        self,
        liquidacion_general,
        liquidacion_io,
        liquidacion_visitas,
        proyecto,
        entidad,
        usuario_id: int,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Construye InspeccionObraPrimeraRevisionResult a partir de objetos ORM.
        Delegates common ORM→Result mapping to core.
        """
        # Delegates common mapping to core (uses denormalized proyecto fields)
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            fecha_registro=str(liquidacion_general.fecha_registro) if liquidacion_general.fecha_registro else "",
        )

        tipo_result = LiquidacionVisitasResult(
            id=str(liquidacion_visitas.id),
            cantidad_visitas=liquidacion_visitas.cantidad_visitas,
            porcentaje_uit=float(liquidacion_visitas.porcentaje_uit),
            categoria=liquidacion_visitas.categoria,
            tarifa_aplicada_id=str(liquidacion_visitas.tarifa_aplicada_id),
            inspectores=self._build_inspectores_result(liquidacion_visitas),
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

    @staticmethod
    def _build_inspectores_result(liquidacion_visitas) -> list:
        """
        Construye los LiquidacionInspectorResult de la IO (asociados al tipo
        LiquidacionPorCategoriaVisitas, no a la general). Retorna [] si no hay.

        Reutiliza PerfilIngenieroResult (dominio de inspector) en lugar de
        duplicar los campos del perfil de ingeniero.
        """
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
            LiquidacionInspectorResult,
            EspecialidadRevisionResult,
        )
        from modules.liquidaciones.domain.results.inspector.inspector_result import (
            PerfilIngenieroResult,
        )
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        inspectores = (
            LiquidacionInspector.objects
            .filter(liquidacion=liquidacion_visitas)
            .select_related(
                "inspector__perfil_ingeniero",
                "especialidad_revision",
            )
            .order_by("created_at")
        )

        resultados = []
        for li in inspectores:
            perfil = li.inspector.perfil_ingeniero
            resultados.append(
                LiquidacionInspectorResult(
                    id=str(li.id),
                    inspector_id=str(li.inspector_id),
                    perfil_ingeniero=PerfilIngenieroResult(
                        id=str(perfil.id),
                        cip=perfil.cip,
                        dni=perfil.dni,
                        nombres=perfil.nombres,
                        apellido_paterno=perfil.apellido_paterno,
                        apellido_materno=perfil.apellido_materno,
                        nombre_completo=perfil.nombre_completo,
                        correo_personal=perfil.correo_personal,
                        correo_institucional=perfil.correo_institucional,
                    ),
                    especialidad_revision=(
                        EspecialidadRevisionResult(
                            id=str(li.especialidad_revision.id),
                            nombre=li.especialidad_revision.nombre,
                        )
                        if li.especialidad_revision
                        else None
                    ),
                    dictamen_revision=li.dictamen_revision,
                    fecha_presentacion=str(li.fecha_presentacion) if li.fecha_presentacion else None,
                    fecha_revision=str(li.fecha_revision) if li.fecha_revision else None,
                )
            )
        return resultados
