"""
LiquidacionesEdificacionesController — controladores HTTP ligeros.

Solo delega a LiquidacionesEdificacionesOrchestrator y retorna vía presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from ..schemas.liquidacion_edificaciones_schemas import (
    PrimeraRevisionLiquidacionWrapperIn,
    PrimeraRevisionLiquidacionIn,
    NuevaRevisionLiquidacionIn,
    LiquidacionEdificacionOut,
    NuevaRevisionFormularioOut,
    RevisionesVigentesOut,
    LiquidacionEdificacionesListItemOut,
    CotizacionPrimeraRevisionWrapperIn,
    CotizacionNuevaRevisionIn,
    CotizacionQuoteOut,
    DelegadosVigentesOut,
    EspecialidadesVigentesOut,
)
from ..presenters.liquidacion_edificaciones_presenter import LiquidacionEdificacionesPresenter
from ...domain.services.orchestrators.liquidacion_edificaciones_orchestrator import LiquidacionesEdificacionesOrchestrator
from ...domain.schemas import ContactoInlineData, ProyectistaInlineData
from ...domain.schemas_proyecto import ProyectoInlineData, EntidadInlineData


@api_controller("/liquidaciones/edificaciones", tags=["Liquidaciones Edificaciones"], permissions=[AllowAny])
class LiquidacionEdificacionesController:
    """
    Controlador para Liquidaciones Edificaciones.

    Endpoints:
    - GET /: Listar liquidaciones con paginación
    - POST /nueva-liquidacion: Crear nueva liquidación (primera revisión)
    - POST /primera-revision: Crear primera revisión (alias de /nueva-liquidacion)
    - POST /cotizar/primera-revision: Cotizar primera revisión sin guardar
    - POST /cotizar/nueva-revision: Cotizar nueva revisión sin guardar
    - GET /nueva-revision/formulario: Preparar formulario para nueva revisión
    - POST /nueva-revision: Crear nueva revisión
    - GET /revisiones-vigentes: Obtener revisiones vigentes
    - GET /especialidades-vigentes: Obtener especialidades vigentes
    - GET /delegados/vigentes: Obtener delegados vigentes
    """

    @inject
    def __init__(self, orchestrator: LiquidacionesEdificacionesOrchestrator):
        self.orchestrator = orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[LiquidacionEdificacionOut]]}, auth=None)
    async def listar_liquidaciones(
        self,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        proyecto_public_id: str = Query(None, description="Filtrar por ID público del proyecto (ej. PROY-2026-00001)"),
    ):
        """
        Listar liquidaciones de edificaciones con paginación.

        Retorna una colección/página de LiquidacionEdificacionOut (estructura plana completa).

        Soporta filtrado opcional por proyecto_public_id.
        """
        result = await self.orchestrator.listar_liquidaciones(
            page=page,
            page_size=page_size,
            proyecto_public_id=proyecto_public_id,
        )

        # Transformar cada LiquidacionEdificacionesListItem a LiquidacionEdificacionOut
        # Para esto necesitamos obtener el detalle completo de cada liquidación
        items_out = []
        for item in result.items:
            detalle = await self.orchestrator.obtener_liquidacion_por_id(str(item.id))
            items_out.append(LiquidacionEdificacionesPresenter.present(detalle))

        total_pages = (result.total + page_size - 1) // page_size if result.total > 0 else 1

        return success_response(PaginatedData(
            items=items_out,
            total=result.total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/nueva-liquidacion", response={200: ApiResponse[LiquidacionEdificacionOut]}, auth=None)
    async def crear_nueva_liquidacion(self, payload: PrimeraRevisionLiquidacionWrapperIn):
        """
        Crear nueva liquidación de edificaciones (primera revisión).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones:
        - El proyecto debe existir
        - La municipalidad debe existir
        - No debe existir ya una primera revisión para ese proyecto
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        - Los proyectistas inline (si se proveen) deben estar habilitados en CIP (condicion='1')
        - Los delegados (si se proveen) deben estar activos y tener periodo vigente
        """
        liquidacion_data = payload.liquidacion

        # Parseo de proyectistas inline desde el payload
        proyectistas_inline = [
            ProyectistaInlineData(
                cip=p.cip,
                especialidad_id=p.especialidad_id,
                descripcion=p.descripcion,
            )
            for p in liquidacion_data.proyectistas
        ] if liquidacion_data.proyectistas else None

        # Proyectistas IDs: convertir a strings si hay contenido, None si está vacío
        # La selección de cuál usar se delega al orchestrator/flujo
        proyectistas_ids = [str(pid) for pid in liquidacion_data.proyectistas_ids] if liquidacion_data.proyectistas_ids else None

        result = await self.orchestrator.crear_primera_revision(
            proyecto_public_id=liquidacion_data.proyecto_public_id,
            municipalidad_id=str(liquidacion_data.municipalidad_id),
            tipo_tramite=liquidacion_data.tipo_tramite,
            valor_proyecto=liquidacion_data.valor_proyecto,
            expediente=liquidacion_data.expediente,
            valor_base_calculo=liquidacion_data.valor_base_calculo,
            observacion=liquidacion_data.observacion,
            revisiones_ids=liquidacion_data.revisiones_ids,
            proyectistas_inline=proyectistas_inline,
            proyectistas_ids=proyectistas_ids,
            # NOTE: delegados_ids fue eliminado de PrimeraRevisionLiquidacionIn (Fase 4).
            # Los delegados se manejarán en un endpoint POST posterior separate.
            contactos_inline=[
                ContactoInlineData(
                    nombres=c.nombres,
                    apellidos=c.apellidos,
                    dni=c.dni,
                    cargo=c.cargo,
                    telefono=c.telefono,
                    celular=c.celular,
                    email=c.email,
                    direccion=c.direccion,
                    principal=c.principal,
                    descripcion=c.descripcion,
                )
                for c in liquidacion_data.contactos
            ],
            proyecto_inline=ProyectoInlineData(
                denominacion=liquidacion_data.proyecto_inline.denominacion,
                direccion=liquidacion_data.proyecto_inline.direccion,
                distrito_id=liquidacion_data.proyecto_inline.distrito_id,
                nombre_propietario=liquidacion_data.proyecto_inline.nombre_propietario,
                entidad=EntidadInlineData(
                    tipo_documento=liquidacion_data.proyecto_inline.entidad.tipo_documento,
                    numero_documento=liquidacion_data.proyecto_inline.entidad.numero_documento,
                    razon_social=liquidacion_data.proyecto_inline.entidad.razon_social,
                ),
            ) if liquidacion_data.proyecto_inline else None,
            # Fase 3: tarifas_ids para selección explícita de tarifa en primera revisión
            tarifas_ids=[str(tid) for tid in liquidacion_data.tarifas_ids] if liquidacion_data.tarifas_ids else None,
        )
        return success_response(LiquidacionEdificacionesPresenter.present(result))

    @route.post("/primera-revision", response={200: ApiResponse[LiquidacionEdificacionOut]}, auth=None)
    async def crear_primera_revision(self, payload: PrimeraRevisionLiquidacionWrapperIn):
        """
        Crear primera revisión de liquidación de edificaciones (alias de /nueva-liquidacion).

        Acepta wrapper { liquidacion: {...} } para alinear con frontend.

        Validaciones:
        - El proyecto debe existir
        - La municipalidad debe existir
        - No debe existir ya una primera revisión para ese proyecto
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        """
        return await self.crear_nueva_liquidacion(payload)

    @route.post("/cotizar/primera-revision", response={200: ApiResponse[CotizacionQuoteOut]}, auth=None)
    async def cotizar_primera_revision(self, payload: CotizacionPrimeraRevisionWrapperIn):
        """
        Cotizar primera revisión sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - valor_proyecto: Valor del proyecto
        - valor_base_calculo: Valor base de cálculo para el cálculo

        La cotización es específica para Edificación — usa TarifaLiquidacionBase
        filtrada por tipo_liquidacion=EDIFICACION.
        """
        liquidacion_data = payload.liquidacion
        result = await self.orchestrator.cotizar_primera_revision(
            tipo_tramite=liquidacion_data.tipo_tramite,
            valor_proyecto=liquidacion_data.valor_proyecto,
            valor_base_calculo=liquidacion_data.valor_base_calculo,
            # Fase 3: tarifas_ids para usar tarifa específica en cotización
            tarifas_ids=[str(tid) for tid in liquidacion_data.tarifas_ids] if liquidacion_data.tarifas_ids else None,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_cotizacion(result))

    @route.post("/cotizar/nueva-revision", response={200: ApiResponse[CotizacionQuoteOut]}, auth=None)
    async def cotizar_nueva_revision(self, payload: CotizacionNuevaRevisionIn):
        """
        Cotizar nueva revisión sin guardar en BD.

        Solo calcula los totales y retorna el resultado de la cotización.
        No crea ningún registro en la base de datos.

        Body:
        - liquidacion_previa_id: ID de la liquidación previa
        - revisiones_ids: IDs de revisiones (NO puede estar vacío — 422 si se envía vacío)

        No requiere valor_proyecto; se obtiene de la liquidación previa.
        """
        result = await self.orchestrator.cotizar_nueva_revision(
            liquidacion_previa_id=str(payload.liquidacion_previa_id),
            revisiones_ids=payload.revisiones_ids,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_cotizacion(result))

    @route.get("/nueva-revision/formulario", response={200: ApiResponse[NuevaRevisionFormularioOut]}, auth=None)
    async def preparar_nueva_revision(
        self,
        liquidacion_previa_id: str = Query(..., description="ID de la liquidación previa (UUID)"),
    ):
        """
        Preparar formulario para nueva revisión.

        Devuelve:
        - Siguiente número de revisión
        - Si cobrará o no
        - Datos del proyecto
        - Revisiones vigentes disponibles
        """
        result = await self.orchestrator.preparar_nueva_revision(
            liquidacion_previa_id=liquidacion_previa_id,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_formulario(result))

    @route.post("/nueva-revision", response={200: ApiResponse[LiquidacionEdificacionOut]}, auth=None)
    async def crear_nueva_revision(self, payload: NuevaRevisionLiquidacionIn):
        """
        Crear nueva revisión de liquidación de edificaciones.

        Validaciones:
        - La liquidación previa debe existir y ser de edificaciones
        - El número de revisión no puede exceder 7
        - Las revisiones seleccionadas deben estar vigentes/habilitadas
        - Proyectistas inline (si se proveen) deben estar habilitados en CIP
        - Delegados (si se proveen) deben estar activos y tener periodo vigente
        - Si se omite proyectistas o está vacío, se heredan de la liquidación previa
        - Si se omite delegados o está vacío, se heredan de la liquidación previa
        """
        # Parseo de proyectistas inline desde el payload
        # La selección de cuál usar (inline vs IDs) se delega al orchestrator/flujo
        proyectistas_inline = [
            ProyectistaInlineData(
                cip=p.cip,
                especialidad_id=p.especialidad_id,
                descripcion=p.descripcion,
            )
            for p in payload.proyectistas
        ] if payload.proyectistas else None

        # Proyectistas IDs: convertir a strings si hay contenido, None si está vacío
        proyectistas_ids = [str(pid) for pid in payload.proyectistas_ids] if payload.proyectistas_ids else None

        result = await self.orchestrator.crear_nueva_revision(
            liquidacion_previa_id=str(payload.liquidacion_previa_id),
            observacion=payload.observacion,
            revisiones_ids=[str(rid) for rid in payload.revisiones_ids],
            proyectistas_inline=proyectistas_inline,
            proyectistas_ids=proyectistas_ids,
            delegados_ids=[str(did) for did in payload.delegados_ids] if payload.delegados_ids else None,
            contactos_inline=[
                ContactoInlineData(
                    nombres=c.nombres,
                    apellidos=c.apellidos,
                    dni=c.dni,
                    cargo=c.cargo,
                    telefono=c.telefono,
                    celular=c.celular,
                    email=c.email,
                    direccion=c.direccion,
                    principal=c.principal,
                    descripcion=c.descripcion,
                )
                for c in payload.contactos
            ],
            # Fase 3 refactor: tarifas_ids para selección explícita en nueva revisión
            tarifas_ids=[str(tid) for tid in payload.tarifas_ids] if payload.tarifas_ids else None,
        )
        return success_response(LiquidacionEdificacionesPresenter.present(result))

    @route.get("/revisiones-vigentes", response={200: ApiResponse[RevisionesVigentesOut]}, auth=None)
    async def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str = Query(None, description="Tipo de trámite de edificación (opcional)"),
        tramite_accion: str = Query(None, description="Acción de trámite: PRIMERA_REVISION o REVISION (opcional)"),
    ):
        """
        Obtiene todas las revisiones/especialidades vigentes para mostrar en formulario.

        Si tipo_tramite y tramite_accion son provistos, filtra las tarifas vigentes
        usando ReglaTarifaEdificacion para esa combinación.

        Retorna lista de revisiones con especialidad, tarifa (derecho_minimo,
        derecho_maximo, porcentaje_minimo_uit) y si está habilitada.
        """
        result = await self.orchestrator.obtener_revisiones_vigentes(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )
        return success_response({'revisiones': result})

    @route.get("/especialidades-vigentes", response={200: ApiResponse[EspecialidadesVigentesOut]}, auth=None)
    async def obtener_especialidades_vigentes(self):
        """
        Obtiene las especialidades vigentes del grupo de EspecialidadesLiquidacion.

        Fuente: grupo EspecialidadesLiquidacion con tipo_liquidacion=EDIFICACION,
        periodo_inicio <= hoy y (periodo_fin IS NULL OR periodo_fin >= hoy).

        Retorna lista de especialidades con: id, nombre.
        """
        result = await self.orchestrator.obtener_especialidades_vigentes()
        return success_response({'especialidades': result})

    @route.get("/delegados/vigentes", response={200: ApiResponse[DelegadosVigentesOut]}, auth=None)
    async def obtener_delegados_vigentes(
        self,
        municipalidad_id: str = Query(..., description="ID de la municipalidad (UUID)"),
        revision_id: str = Query(..., description="ID de la revisión de edificación (UUID)"),
        categoria: str = Query(None, description="Categoría del delegado: Edificaciones o Habilitaciones Urbanas"),
    ):
        """
        Obtiene delegados vigentes para una municipalidad y revisión seleccionadas.

        Un delegado está vigente si:
        - Pertenece a la municipalidad (MunicipalidadesDelegado con activo=True)
        - Tiene status='activo'
        - Tiene un periodo vigente para la fecha actual
        - Su especialidad está en el grupo EspecialidadesLiquidacion vigente
        - Su especialidad también está en las especialidades de la TarifaLiquidacionBase seleccionada
        - Si se provee categoria, filtra por esa categoría (por defecto Edificaciones para este endpoint)

        Args:
            municipalidad_id: UUID de la municipalidad
            revision_id: UUID opcional de TarifaLiquidacionBase para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas). Default: Edificaciones

        Returns:
            Lista de delegados con: id, nombre_completo, cip, especialidad: {id, nombre}, tipo.
        """
        result = await self.orchestrator.obtener_delegados_vigentes(
            municipalidad_id=municipalidad_id,
            revision_id=revision_id,
            categoria=categoria,
        )
        return success_response(LiquidacionEdificacionesPresenter.present_delegados_vigentes(result))

    # ── Ruta con parámetro path al FINAL para evitar capturar rutas estáticas ──────

    @route.get("/{liquidacion_id}", response={200: ApiResponse[LiquidacionEdificacionOut]}, auth=None)
    async def obtener_detalle_liquidacion(
        self,
        liquidacion_id: str,
    ):
        """
        Obtener detalle de una liquidación de edificación por ID.

        Retorna un objeto plano LiquidacionEdificacionOut con todos los campos.
        """
        result = await self.orchestrator.obtener_liquidacion_por_id(liquidacion_id)
        return success_response(LiquidacionEdificacionesPresenter.present(result))
