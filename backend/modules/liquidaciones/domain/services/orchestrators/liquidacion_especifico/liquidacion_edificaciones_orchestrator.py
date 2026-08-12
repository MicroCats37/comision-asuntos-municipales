"""
Orchestrator for Edificaciones (PorcentajeObra) first revision.

Validates input, applies per-detail clamping,
maps Presentation Schema -> Domain DTO.

Architecture: Orchestrator owns business rules (clamping). No @transaction.atomic.
"""
from decimal import Decimal
from typing import List
import uuid
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError
from modules.liquidaciones.domain.constants import TipoLiquidacion, MAX_REVISIONES
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_edificaciones_flujo import (
    LiquidacionEdificacionesFlujo,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
    ContactoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    DatosPorcentajeObra,
    LiquidacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.edificaciones_primera_revision_data import (
    EdificacionesPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.edificaciones_primera_revision_result import (
    EdificacionesPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
    CotizacionPorcentajeObraDetalleResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraTarifaIn,
)
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError


from django.core.exceptions import ObjectDoesNotExist

class LiquidacionEdificacionesOrchestrator:
    """
    Orchestrator for Edificaciones (PorcentajeObra).
    
    Mirrors the MecanicaSuelos pattern but:
    - Uses PorcentajeObra Core service (not M2)
    - Handles hybrid resolution (auto-fill vs explicit tarifas)
    - tipo_tramite stays NULL for now (FUTURE comment)
    """
    
    def _validar_tarifa_explicita(self, tarifa) -> None:
        """
        Validates an explicitly-provided tarifa in the input.
        Raises HttpError if invalid.
        """
        today = timezone.now().date()
        is_vigente = (
            tarifa.tarifa_base.periodo_inicio <= today
            and (
                tarifa.tarifa_base.periodo_fin is None
                or tarifa.tarifa_base.periodo_fin >= today
            )
        )
        if not is_vigente:
            raise HttpError(400, f"Tarifa {tarifa.id} no está vigente")
        if tarifa.tarifa_base.tipo_liquidacion.codigo != TipoLiquidacion.EDIFICACION:
            raise HttpError(400, f"Tarifa {tarifa.id} no es de edificaciones")
    
    @inject
    def __init__(
        self,
        porcentaje_core_service: LiquidacionPorcentajeObraCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        flujo: LiquidacionEdificacionesFlujo,
    ):
        self.porcentaje_core = porcentaje_core_service
        self.general_core = general_core_service
        self.flujo = flujo
    
    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Validates input, resolves tarifas (hybrid), calculates, delegates to Flujo.
        
        Flow:
        1. Validate valor_declarado > 0
        2. Resolve tarifas (auto-fill or explicit validation)
        3. Validate IGV/UIT vigentes exist
        4. Build domain DTO
        5. Delegate to Flujo
        """
        # Step 1: Validation
        valor_declarado = payload_in.liquidacion_especifica.datos.valor_declarado
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        
        # Step 2: Hybrid resolution
        payload_tarifas_ids = [
            str(t.tarifa_porcentaje_obra_id)
            for t in payload_in.liquidacion_especifica.tarifas
        ]
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.EDIFICACION)
        
        # Validate each tarifa (only in explicit mode)
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa)
        
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")
        
        # Step 3: Get vigente IGV and UIT
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")
        
        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")
        
        # Step 4: Build domain DTO
        tarifas_aplicadas = [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.id),
                porcentaje_liquidacion=t.porcentaje_liquidacion,
                especialidad_id=str(t.especialidad.id),
                especialidad_nombre=t.especialidad.nombre,
            )
            for t in tarifas
        ]
        
        domain_data = EdificacionesPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                  municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                  expediente=payload_in.liquidacion_general.expediente,
                  observacion=payload_in.liquidacion_general.observacion,
                  retencion=getattr(payload_in.liquidacion_general, "retencion", False),
                proyecto=ProyectoData(
                    denominacion=payload_in.liquidacion_general.proyecto.denominacion,
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id),
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
                # FUTURE: when tipo_tramite is added, pass payload_in.tipo_tramite here
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=None,  # FUTURE: activate when frontend sends it
            ),
        )
        
        # Step 5: Delegate to Flujo
        return self.flujo.ejecutar_primera_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
        )

    def obtener_tarifas_vigentes_proceso(self):
        """
        Fetches currently active TarifaPorcentajeObra list for Edificaciones.
        Returns List[TarifaPorcentajeObra].
        """
        return self.porcentaje_core.get_tarifas_porcentaje_vigentes(TipoLiquidacion.EDIFICACION)

    def cotizar_proceso(
        self,
        valor_declarado: Decimal,
        tarifas_input: List[LiquidacionPorcentajeObraTarifaIn],
    ) -> CotizacionPorcentajeObraResult:
        """
        Quote-only calculation. Does NOT persist.

        Same hybrid resolution as crear_primera_revision_proceso.
        Returns CotizacionPorcentajeObraResult with totals and per-detalle breakdown.
        """
        # Step 1: Validation
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 2: Hybrid resolution
        payload_tarifas_ids = [str(t.tarifa_porcentaje_obra_id) for t in tarifas_input]
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.EDIFICACION)

        # Validate explicit mode
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa)
        
        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")
        
        # Step 3: Get vigente IGV, UIT and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente")
        if not uit_vigente:
            raise HttpError(400, "No hay UIT vigente configurado")
        
        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")
        
        # Step 4: Calculate
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=valor_declarado,
            tarifas=tarifas,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
        )
        
        # Step 5: Build result
        return CotizacionPorcentajeObraResult(
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado_id=cotizacion.derecho_aplicado_id,
            detalles=[
                CotizacionPorcentajeObraDetalleResult(
                    tarifa_id=d.tarifa_aplicada.tarifa_id,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv,
                    uit=d.uit,
                    total=d.total,
                )
                for d in cotizacion.detalles
            ],
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )

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
    ) -> tuple[List[EdificacionesPrimeraRevisionResult], int]:
        """
        Returns paginated EdificacionesPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[EdificacionesPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core.list_liquidaciones_by_type_paginated(
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
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

        # Build EdificacionesPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[EdificacionesPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_edificaciones_result(lg))

        return domain_results, total

    def _build_edificaciones_result(self, lg) -> EdificacionesPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to EdificacionesPrimeraRevisionResult domain DTO.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.edificaciones_primera_revision_result import (
            LiquidacionEspecificaEdificacionesResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
            LiquidacionGeneralResult,
            EntidadResult,
            ProyectoResult,
            UsuarioCreadorResult,
            MunicipalidadResult,
            IgvResult,
            UitResult,
            DistritoResult,
            ProvinciaResult,
            DepartamentoResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
            LiquidacionPorcentajeObraResult,
            DetallePorcentajeObraResult,
        )

        proyecto = lg.proyecto
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # La razon social/tipo/numero viven DENORMALIZADOS en Proyecto
        # (el modelo Entidad no tiene razon_social). Usar siempre los del proyecto.
        ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
        ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
        ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None

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

        general_result = LiquidacionGeneralResult(
            id=str(lg.id),
            municipalidad=MunicipalidadResult(
                id=str(lg.municipalidad.id),
                codigo=lg.municipalidad.codigo,
                nombre=lg.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(lg.usuario_creador.id) if lg.usuario_creador else "00000000-0000-0000-0000-000000000000",
                nombres=getattr(lg.usuario_creador, "nombres", None),
                apellidos=getattr(lg.usuario_creador, "apellidos", None),
                email=getattr(lg.usuario_creador, "email", None),
                dni=getattr(lg.usuario_creador, "dni", None),
                username=getattr(lg.usuario_creador, "username", None),
            ),
            fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
            expediente=lg.expediente or "",
            observacion=lg.observacion,
            numero_revision=lg.numero_revision,
            sub_total=float(lg.sub_total) if lg.sub_total else 0.0,
            total=float(lg.total) if lg.total else 0.0,
            retencion=lg.retencion,
            igv=(
                IgvResult(
                    id=str(lg.igv_id.id),
                    valor=float(lg.igv_id.valor),
                    periodo_inicio=lg.igv_id.periodo_inicio.isoformat() if lg.igv_id.periodo_inicio else None,
                )
                if lg.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(lg.uit_id.id),
                    valor=float(lg.uit_id.valor),
                    periodo_inicio=lg.uit_id.periodo_inicio.isoformat() if lg.uit_id.periodo_inicio else None,
                )
                if lg.uit_id
                else None
            ),
            proyecto=ProyectoResult(
                id=str(proyecto.id),
                denominacion=proyecto.denominacion,
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito=distrito_result,
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
        )

        edificacion = lg.edificaciones
        especifica_result = LiquidacionEspecificaEdificacionesResult(
            id=str(edificacion.id),
            numero=edificacion.numero,
        )

        lpo = lg.liquidacion_porcentaje_obra
        tipo_result = LiquidacionPorcentajeObraResult(
            id=str(lpo.id),
            liquidacion_general_id=str(lpo.liquidacion_general_id),
            tipo_tramite=lpo.tipo_tramite,
            valor_declarado=lpo.valor_declarado,
            porcentaje_liquidacion=lpo.porcentaje_liquidacion,
            derecho_minimo=lpo.derecho_minimo,
            derecho_maximo=lpo.derecho_maximo,
            porcentaje_minimo_uit=lpo.porcentaje_minimo_uit,
            derecho_aplicado_id=str(lpo.derecho_aplicado_id),
            detalles=[
                DetallePorcentajeObraResult(
                    id=str(d.id),
                    tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                    especialidad_id=str(d.especialidad_id),
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv or Decimal("0"),
                    uit=d.uit or Decimal("0"),
                    total=d.total or Decimal("0"),
                )
                for d in lpo.detalles.all()
            ],
        )

        # Build revisiones_previas from M2M
        from modules.liquidaciones.domain.results.liquidacion_especifico.edificaciones_primera_revision_result import (
            LiquidacionPreviaResult,
        )
        revisiones_previas = [
            LiquidacionPreviaResult(
                id=str(lp.id),
                numero_revision=lp.numero_revision,
                expediente=lp.expediente or "",
            )
            for lp in lg.liquidaciones_previas.all().order_by('numero_revision')
        ]
        # También exponer en el LiquidacionGeneralResult (campo general)
        general_result.revisiones_previas = revisiones_previas

        return EdificacionesPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
            revisiones_previas=revisiones_previas,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> EdificacionesPrimeraRevisionResult:
        """
        Returns a single EdificacionesPrimeraRevisionResult for Edificaciones by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_id)
            return self._build_edificaciones_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")

    def crear_nueva_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
        liquidacion_previa_id: uuid.UUID,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Validates and creates a new revision (3 or 5) for an existing Edificaciones liquidacion.

        Validations:
        - liquidacion_previa_id exists and is Edificaciones
        - numero_revision follows pattern: previa + 2 (1→3, 3→5)
        - MAX_REVISIONES not exceeded
        - Same proyecto as previa
        - No duplicate revision for proyecto
        - Tarifas vigentes

        For revision 5: liquidaciones_previas M2M must include BOTH revision 1 AND 3.
        """
        # Step 1: Validate liquidacion_previa exists and is Edificaciones
        try:
            previa = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, f"Liquidación previa {liquidacion_previa_id} no encontrada")

        proyecto = previa.proyecto

        # Step 2: Calculate new numero_revision
        nueva_revision_numero = previa.numero_revision + 2
        if nueva_revision_numero > MAX_REVISIONES:
            raise HttpError(400, f"MAX_REVISIONES={MAX_REVISIONES} excedido. No se puede crear revisión {nueva_revision_numero}")

        # Step 3: Validate even revision numbers not allowed (sanity check)
        if nueva_revision_numero % 2 == 0:
            raise HttpError(400, f"Solo se permiten revisiones impares (1, 3, 5). No se puede crear revisión {nueva_revision_numero}")

        # Step 4: For revision 3, must have revision 1 in chain; for revision 5, must have 1 and 3
        if nueva_revision_numero == 3:
            # Need revision 1 to exist
            revision_1 = self.general_core.get_ultima_revision_por_proyecto(
                proyecto_id=proyecto.id,
                tipo_liquidacion=TipoLiquidacion.EDIFICACION,
            )
            # The ultima revision should be the previa (which should be revision 1)
            if not previa.numero_revision == 1:
                raise HttpError(400, f"Para crear revisión 3, la liquidación previa debe ser revisión 1. Se proporcionó revisión {previa.numero_revision}")
        elif nueva_revision_numero == 5:
            # Need revisions 1 AND 3 to exist
            # Check previa is revision 3
            if previa.numero_revision != 3:
                raise HttpError(400, f"Para crear revisión 5, la liquidación previa debe ser revisión 3. Se proporcionó revisión {previa.numero_revision}")
            # Also verify revision 1 exists via transitive chain
            # The M2M liquidaciones_previas on previa should have revision 1
            if not previa.liquidaciones_previas.filter(numero_revision=1).exists():
                raise HttpError(400, "Para crear revisión 5, debe existir revisión 1 en el proyecto")

        # Step 5: Validate same proyecto (already implicit since we're using previa's proyecto)

        # Step 6: Check no duplicate revision for this proyecto
        existente = self.general_core.get_ultima_revision_por_proyecto(
            proyecto_id=proyecto.id,
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        )
        if existente and existente.numero_revision == nueva_revision_numero:
            raise HttpError(400, f"Ya existe una liquidación con revisión {nueva_revision_numero} para este proyecto")

        # Step 7: valor_declarado se HEREDA de la previa (no viene en el input de nueva revision)
        valor_declarado = previa.liquidacion_porcentaje_obra.valor_declarado
        if valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 8: Resolve tarifas (same as primera revision)
        payload_tarifas_ids = [
            str(t.tarifa_porcentaje_obra_id)
            for t in payload_in.liquidacion_especifica.tarifas
        ]
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.EDIFICACION)

        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")

        # Step 9: Get vigente IGV, UIT and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 10: Build domain DTO (same structure as primera revision but with different data)
        tarifas_aplicadas = [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.id),
                porcentaje_liquidacion=t.porcentaje_liquidacion,
                especialidad_id=str(t.especialidad.id),
                especialidad_nombre=t.especialidad.nombre,
            )
            for t in tarifas
        ]

        domain_data = EdificacionesPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente or previa.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                retencion=getattr(payload_in.liquidacion_general, "retencion", False),
                proyecto=ProyectoData(
                    denominacion=proyecto.denominacion,
                    nombre_propietario=proyecto.nombre_propietario,
                    direccion=proyecto.direccion,
                    distrito_id=str(proyecto.distrito_id),
                    entidad_razon_social=proyecto.entidad_razon_social,
                    entidad=EntidadData(
                        tipo_documento=proyecto.entidad_tipo_documento,
                        numero_documento=proyecto.entidad_numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=None,
            ),
        )

        # Step 11: Delegate to Flujo with previa_id and previa objects for M2M
        return self.flujo.ejecutar_nueva_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
            liquidacion_previa=previa,
        )

    def obtener_ultima_revision_proceso(
        self,
        proyecto_id: uuid.UUID,
        razon_social: str = None,
        numero_documento: str = None,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Returns the liquidacion with the highest numero_revision for a proyecto.
        Optional filters by razon_social and numero_documento of the proyecto's entidad.
        """
        # First find the proyecto to validate filters
        from modules.liquidaciones.domain.models.proyecto import Proyecto
        try:
            proyecto = Proyecto.objects.get(id=proyecto_id)
        except ObjectDoesNotExist:
            raise HttpError(404, f"Proyecto {proyecto_id} no encontrado")

        # Apply optional filters
        if razon_social and razon_social not in (proyecto.entidad_razon_social or ""):
            raise HttpError(400, "razon_social no coincide con el proyecto")
        if numero_documento and numero_documento != proyecto.entidad_numero_documento:
            raise HttpError(400, "numero_documento no coincide con el proyecto")

        # Get ultima revision
        lg = self.general_core.get_ultima_revision_por_proyecto(
            proyecto_id=proyecto_id,
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        )
        if not lg:
            raise HttpError(404, f"No se encontró liquidación para el proyecto {proyecto_id}")

        return self._build_edificaciones_result(lg)
