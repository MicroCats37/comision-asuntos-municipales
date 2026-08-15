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
    InspeccionObraNuevaRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
    LiquidacionEspecificaInspeccionObraResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    LiquidacionDelegadoEnGeneralResult,
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
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.INSPECCION_OBRA),
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
            ProyectoResult, EntidadResult, UsuarioCreadorResult, MunicipalidadResult, IgvResult, UitResult,
            DistritoResult, ProvinciaResult, DepartamentoResult, TipoLiquidacionResult,
        )

        entidad_result = None
        if entidad:
            entidad_result = EntidadResult(
                razon_social=proyecto.entidad_razon_social,
                tipo_documento=entidad.tipo_documento,
                numero_documento=entidad.numero_documento,
            )

        # Build distrito objeto (con provincia/departamento)
        distrito_result = None
        if getattr(proyecto, "distrito_id", None):
            distrito = proyecto.distrito
            if distrito:
                distrito_result = DistritoResult(
                    id=str(distrito.id),
                    nombre=distrito.nombre,
                    ubigeo=getattr(distrito, "ubigeo", None),
                    provincia=(
                        ProvinciaResult(
                            id=str(distrito.provincia.id),
                            nombre=distrito.provincia.nombre,
                        )
                        if distrito.provincia
                        else None
                    ),
                    departamento=(
                        DepartamentoResult(
                            id=str(distrito.provincia.departamento.id),
                            nombre=distrito.provincia.departamento.nombre,
                        )
                        if distrito.provincia and distrito.provincia.departamento
                        else None
                    ),
                )

        proyecto_result = ProyectoResult(
            id=str(proyecto.id),
            denominacion=proyecto.denominacion,
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            distrito=distrito_result,
            entidad=entidad_result,
        )

        # Build delegados list
        delegados = [
            LiquidacionDelegadoEnGeneralResult(
                id=str(ld.id),
                liquidacion_id=str(liquidacion_general.id),
                delegado_id=str(ld.delegado_id),
                especialidad_revision_id=str(ld.especialidad_revision_id),
                especialidad_revision_nombre=ld.especialidad_revision.nombre,
                delegado_cip=ld.delegado.perfil_ingeniero.cip,
                delegado_dni=ld.delegado.perfil_ingeniero.dni,
                delegado_nombre_completo=ld.delegado.perfil_ingeniero.nombre_completo,
                periodo=ld.periodo,
                dictamen_revision=ld.dictamen_revision,
                fecha_presentacion=ld.fecha_presentacion.isoformat() if ld.fecha_presentacion else None,
                fecha_revision=ld.fecha_revision.isoformat() if ld.fecha_revision else None,
            )
            for ld in getattr(liquidacion_general, 'liquidacion_delegados', []).all()
        ]

        general_result = LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            municipalidad=MunicipalidadResult(
                id=str(liquidacion_general.municipalidad.id),
                codigo=liquidacion_general.municipalidad.codigo,
                nombre=liquidacion_general.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(usuario_id),
                nombres=getattr(liquidacion_general.usuario_creador, "nombres", None),
                apellidos=getattr(liquidacion_general.usuario_creador, "apellidos", None),
                email=getattr(liquidacion_general.usuario_creador, "email", None),
                dni=getattr(liquidacion_general.usuario_creador, "dni", None),
                username=getattr(liquidacion_general.usuario_creador, "username", None),
            ),
            fecha_registro=str(liquidacion_general.fecha_registro) if liquidacion_general.fecha_registro else "",
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            retencion=gen_data.retencion,
            igv=(
                IgvResult(
                    id=str(liquidacion_general.igv_id.id),
                    valor=float(liquidacion_general.igv_id.valor),
                    periodo_inicio=liquidacion_general.igv_id.periodo_inicio.isoformat() if liquidacion_general.igv_id.periodo_inicio else None,
                )
                if liquidacion_general.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(liquidacion_general.uit_id.id),
                    valor=float(liquidacion_general.uit_id.valor),
                    periodo_inicio=liquidacion_general.uit_id.periodo_inicio.isoformat() if liquidacion_general.uit_id.periodo_inicio else None,
                )
                if liquidacion_general.uit_id
                else None
            ),
            proyecto=proyecto_result,
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=liquidacion_general.tipo_liquidacion.codigo,
                    nombre=liquidacion_general.tipo_liquidacion.nombre,
                )
                if liquidacion_general.tipo_liquidacion
                else None
            ),
            delegados=delegados,
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
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general import LiquidacionGeneral
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

        # 6. Crear LiquidacionInspector (asocia el inspector a la liquidación)
        LiquidacionInspector.objects.create(
            liquidacion=liquidacion_general,
            inspector=inspector,
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
        Extrae la lógica de mapeo de ejecutar_primera_revision para reutilización.
        """
        from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
            ProyectoResult, EntidadResult, UsuarioCreadorResult, MunicipalidadResult, IgvResult, UitResult,
            DistritoResult, ProvinciaResult, DepartamentoResult, TipoLiquidacionResult,
        )

        entidad_result = None
        if entidad:
            entidad_result = EntidadResult(
                razon_social=proyecto.entidad_razon_social,
                tipo_documento=entidad.tipo_documento,
                numero_documento=entidad.numero_documento,
            )

        # Build distrito objeto (con provincia/departamento)
        distrito_result = None
        if getattr(proyecto, "distrito_id", None):
            distrito = proyecto.distrito
            if distrito:
                distrito_result = DistritoResult(
                    id=str(distrito.id),
                    nombre=distrito.nombre,
                    ubigeo=getattr(distrito, "ubigeo", None),
                    provincia=(
                        ProvinciaResult(
                            id=str(distrito.provincia.id),
                            nombre=distrito.provincia.nombre,
                        )
                        if distrito.provincia
                        else None
                    ),
                    departamento=(
                        DepartamentoResult(
                            id=str(distrito.provincia.departamento.id),
                            nombre=distrito.provincia.departamento.nombre,
                        )
                        if distrito.provincia and distrito.provincia.departamento
                        else None
                    ),
                )

        proyecto_result = ProyectoResult(
            id=str(proyecto.id),
            denominacion=proyecto.denominacion,
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            distrito=distrito_result,
            entidad=entidad_result,
        )

        # Build delegados list
        delegados = [
            LiquidacionDelegadoEnGeneralResult(
                id=str(ld.id),
                liquidacion_id=str(liquidacion_general.id),
                delegado_id=str(ld.delegado_id),
                especialidad_revision_id=str(ld.especialidad_revision_id),
                especialidad_revision_nombre=ld.especialidad_revision.nombre,
                delegado_cip=ld.delegado.perfil_ingeniero.cip,
                delegado_dni=ld.delegado.perfil_ingeniero.dni,
                delegado_nombre_completo=ld.delegado.perfil_ingeniero.nombre_completo,
                periodo=ld.periodo,
                dictamen_revision=ld.dictamen_revision,
                fecha_presentacion=ld.fecha_presentacion.isoformat() if ld.fecha_presentacion else None,
                fecha_revision=ld.fecha_revision.isoformat() if ld.fecha_revision else None,
            )
            for ld in getattr(liquidacion_general, 'liquidacion_delegados', []).all()
        ]

        general_result = LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            municipalidad=MunicipalidadResult(
                id=str(liquidacion_general.municipalidad.id),
                codigo=liquidacion_general.municipalidad.codigo,
                nombre=liquidacion_general.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(usuario_id),
                nombres=getattr(liquidacion_general.usuario_creador, "nombres", None),
                apellidos=getattr(liquidacion_general.usuario_creador, "apellidos", None),
                email=getattr(liquidacion_general.usuario_creador, "email", None),
                dni=getattr(liquidacion_general.usuario_creador, "dni", None),
                username=getattr(liquidacion_general.usuario_creador, "username", None),
            ),
            fecha_registro=str(liquidacion_general.fecha_registro) if liquidacion_general.fecha_registro else "",
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            retencion=liquidacion_general.retencion,
            igv=(
                IgvResult(
                    id=str(liquidacion_general.igv_id.id),
                    valor=float(liquidacion_general.igv_id.valor),
                    periodo_inicio=liquidacion_general.igv_id.periodo_inicio.isoformat() if liquidacion_general.igv_id.periodo_inicio else None,
                )
                if liquidacion_general.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(liquidacion_general.uit_id.id),
                    valor=float(liquidacion_general.uit_id.valor),
                    periodo_inicio=liquidacion_general.uit_id.periodo_inicio.isoformat() if liquidacion_general.uit_id.periodo_inicio else None,
                )
                if liquidacion_general.uit_id
                else None
            ),
            proyecto=proyecto_result,
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=liquidacion_general.tipo_liquidacion.codigo,
                    nombre=liquidacion_general.tipo_liquidacion.nombre,
                )
                if liquidacion_general.tipo_liquidacion
                else None
            ),
            delegados=delegados,
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
