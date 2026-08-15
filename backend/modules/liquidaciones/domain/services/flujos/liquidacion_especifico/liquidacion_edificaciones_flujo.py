"""
Flujo for Edificaciones (PorcentajeObra) first revision.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from decimal import Decimal
from django.db import transaction
from injector import inject
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.edificaciones_primera_revision_data import (
    EdificacionesPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.edificaciones_primera_revision_result import (
    LiquidacionEspecificaEdificacionesResult,
    EdificacionesPrimeraRevisionResult,
    LiquidacionPreviaResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    LiquidacionDelegadoEnGeneralResult,
    ProyectoResult,
    EntidadResult,
    UsuarioCreadorResult,
    ContactoResult,
    MunicipalidadResult,
    IgvResult,
    UitResult,
    DistritoResult,
    ProvinciaResult,
    DepartamentoResult,
    TipoLiquidacionResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    LiquidacionPorcentajeObraResult,
    DetallePorcentajeObraResult,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionEdificacionesFlujo:
    """
    Flujo for Edificaciones primera revisión.
    
    Order of DB operations:
    1. Entidad (upsert)
    2. Proyecto
    3. LiquidacionGeneral (sub_total=0, total=0 initially)
    4. LiquidacionPorcentajeObra (with detalles) — via Core
    5. LiquidacionEdificacion (identity wrapper)
    
    All in @transaction.atomic.
    """
    
    @inject
    def __init__(
        self,
        porcentaje_core: LiquidacionPorcentajeObraCoreService,
        general_core: LiquidacionGeneralCoreService,
    ):
        self.porcentaje_core = porcentaje_core
        self.general_core = general_core
    
    def ejecutar_primera_revision(
        self,
        usuario_id: int,
        data: EdificacionesPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> EdificacionesPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data, igv_porcentaje, derecho, uit_valor)
    
    @transaction.atomic()
    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: EdificacionesPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> EdificacionesPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica
        
        # Paso 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )
        
        # Paso 2: Proyecto
        proyecto_data = {
            "denominacion": gen_data.proyecto.denominacion,
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)
        
        # Paso 2.5: Contacto principal (inline, opcional)
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.create_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )
        
        # Paso 3: LiquidacionGeneral (with totals=0 initially)
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
              municipalidad_id=gen_data.municipalidad_id,
              expediente=gen_data.expediente,
              observacion=gen_data.observacion,
              retencion=gen_data.retencion,
              proyecto=proyecto,
              tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.EDIFICACION),
              numero_revision=1,
              contacto=contacto,
          )
        
        # Get IGV/UIT FKs for snapshot
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id
        
        # Paso 4: Calculate PorcentajeObra
        # With tarifa-unica-especialidades: po_data.tarifas already contains
        # TarifaPorcentajeObraAplicada DTOs with explicit especialidad from input.
        # Pass DTOs directly to calcular_cotizacion_po (no ORM reconstruction needed).
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,  # DTOs with explicit especialidad
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )
        
        # Step 5: Set LiquidacionGeneral totals from cotizacion
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.save()
        
        # Paso 6: Create LiquidacionPorcentajeObra + detalles
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
        )
        
        # Paso 7: LiquidacionEdificacion (identity wrapper)
        edificacion = LiquidacionEdificacion.objects.create(
            liquidacion=liquidacion_general
        )
        
        # Build Result
        return self._build_result(
            liquidacion_general=liquidacion_general,
            edificacion=edificacion,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    def ejecutar_nueva_revision(
        self,
        usuario_id: int,
        data: EdificacionesPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Creates a new revision (3 or 5) for an existing Edificaciones liquidacion.

        Key differences from primera_revision:
        - Reuses existing Entidad/Proyecto (no upsert needed, already exists)
        - Contact upsert by ALL fields (nombres, apellidos, dni, cargo, telefono, celular, email)
        - Creates new LiquidacionGeneral with numero_revision = previa.numero_revision + 2
        - Sets up M2M liquidaciones_previas (for revision 5, includes BOTH revision 1 AND 3)
        - Creates LiquidacionPorcentajeObra + LiquidacionEdificacion

        For revision 5, the M2M chain is transitive: if previa is revision 3, and revision 3's
        M2M already has revision 1, then the new revision 5's M2M should include both 1 and 3.
        """
        return self._ejecutar_nueva_revision_sync(
            usuario_id=usuario_id,
            data=data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
            liquidacion_previa=liquidacion_previa,
        )

    @transaction.atomic()
    def _ejecutar_nueva_revision_sync(
        self,
        usuario_id: int,
        data: EdificacionesPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> EdificacionesPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Entidad and Proyecto already exist — get them from previa
        proyecto = liquidacion_previa.proyecto
        entidad = proyecto.entidad

        # Contacto upsert by ALL fields
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.upsert_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Calculate new numero_revision
        nueva_revision_numero = liquidacion_previa.numero_revision + 2

        # LiquidacionGeneral (with totals=0 initially)
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(liquidacion_previa.municipalidad_id),
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            retencion=gen_data.retencion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.EDIFICACION),
            numero_revision=nueva_revision_numero,
            contacto=contacto,
        )

        # Get IGV/UIT FKs for snapshot
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id

        # Calculate PorcentajeObra
        # With tarifa-unica-especialidades: po_data.tarifas already contains
        # TarifaPorcentajeObraAplicada DTOs with explicit especialidad from input.
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,  # DTOs with explicit especialidad
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Set LiquidacionGeneral totals from cotizacion
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.save()

        # Create LiquidacionPorcentajeObra + detalles
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
        )

        # LiquidacionEdificacion (identity wrapper)
        edificacion = LiquidacionEdificacion.objects.create(
            liquidacion=liquidacion_general
        )

        # M2M liquidaciones_previas:
        # For revision 3: add previa (which is revision 1)
        # For revision 5: add previa (revision 3) AND all of previa's liquidaciones_previas (revision 1)
        liquidacion_general.liquidaciones_previas.add(liquidacion_previa)
        if nueva_revision_numero == 5:
            # Add all previous liquidaciones from the chain (transitive: revision 3 already has revision 1)
            for liq_prev in liquidacion_previa.liquidaciones_previas.all():
                liquidacion_general.liquidaciones_previas.add(liq_prev)

        # Build Result with revisiones_previas
        return self._build_result_with_previas(
            liquidacion_general=liquidacion_general,
            edificacion=edificacion,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    def _build_result_with_previas(
        self,
        liquidacion_general,
        edificacion,
        liquidacion_po,
        usuario_id: int,
    ) -> EdificacionesPrimeraRevisionResult:
        """
        Maps ORM objects to domain Result including revisiones_previas.
        """
        liquidacion_general.refresh_from_db()

        # Build previas list
        revisiones_previas = [
            LiquidacionPreviaResult(
                id=str(lp.id),
                numero_revision=lp.numero_revision,
                expediente=lp.expediente or "",
            )
            for lp in liquidacion_general.liquidaciones_previas.all().order_by('numero_revision')
        ]

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

        # Build EntidadResult
        entidad_result = None
        if hasattr(liquidacion_general, 'proyecto') and liquidacion_general.proyecto:
            proyecto = liquidacion_general.proyecto
            if hasattr(proyecto, 'entidad_razon_social') and proyecto.entidad_razon_social:
                entidad_result = EntidadResult(
                    razon_social=proyecto.entidad_razon_social,
                    tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None) or "",
                    numero_documento=getattr(proyecto, 'entidad_numero_documento', None) or "",
                )

        # Build ProyectoResult
        proyecto = liquidacion_general.proyecto
        distrito_result = None
        if proyecto.distrito_id:
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
                            departamento=(
                                DepartamentoResult(
                                    id=str(distrito.provincia.departamento.id),
                                    nombre=distrito.provincia.departamento.nombre,
                                )
                                if distrito.provincia.departamento
                                else None
                            ),
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

        # Build ContactoResult
        contacto_result = None
        if liquidacion_general.contacto:
            contacto = liquidacion_general.contacto
            contacto_result = ContactoResult(
                id=str(contacto.id),
                nombres=contacto.nombres,
                apellidos=contacto.apellidos,
                dni=contacto.dni,
                cargo=contacto.cargo,
                telefono=contacto.telefono,
                celular=contacto.celular,
                email=contacto.email,
            )

        return EdificacionesPrimeraRevisionResult(
            liquidacion_general=LiquidacionGeneralResult(
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
                fecha_registro=liquidacion_general.created_at.isoformat(),
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
                contacto=contacto_result,
                revisiones_previas=revisiones_previas,
                delegados=delegados,
                tipo_liquidacion=(
                    TipoLiquidacionResult(
                        codigo=liquidacion_general.tipo_liquidacion.codigo,
                        nombre=liquidacion_general.tipo_liquidacion.nombre,
                    )
                    if liquidacion_general.tipo_liquidacion
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaEdificacionesResult(
                id=str(edificacion.id),
                numero=edificacion.numero,
            ),
            liquidacion_tipo=LiquidacionPorcentajeObraResult(
                id=str(liquidacion_po.id),
                liquidacion_general_id=str(liquidacion_po.liquidacion_general_id),
                tipo_tramite=liquidacion_po.tipo_tramite,
                valor_declarado=liquidacion_po.valor_declarado,
                porcentaje_liquidacion=liquidacion_po.porcentaje_liquidacion,
                derecho_minimo=liquidacion_po.derecho_minimo,
                derecho_maximo=liquidacion_po.derecho_maximo,
                porcentaje_minimo_uit=liquidacion_po.porcentaje_minimo_uit,
                derecho_aplicado_id=str(liquidacion_po.derecho_aplicado_id),
                detalles=[
                    DetallePorcentajeObraResult(
                        id=str(d.id),
                        tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                        especialidad_id=str(d.especialidad_id),
                        porcentaje_aplicado=d.porcentaje_aplicado,
                        subtotal=d.subtotal,
                        igv=d.igv,
                        uit=d.uit,
                        total=d.total,
                    )
                    for d in liquidacion_po.detalles.all()
                ],
            ),
            revisiones_previas=revisiones_previas,
        )
    
    def _build_result(
        self,
        liquidacion_general,
        edificacion,
        liquidacion_po,
        usuario_id: int,
    ) -> EdificacionesPrimeraRevisionResult:
        """Maps ORM objects to domain Result."""
        # Refresh to get calculated fields
        liquidacion_general.refresh_from_db()

        # Primera revisión: no hay previas
        revisiones_previas = []

        # Build EntidadResult
        entidad_result = None
        if hasattr(liquidacion_general, 'proyecto') and liquidacion_general.proyecto:
            proyecto = liquidacion_general.proyecto
            if hasattr(proyecto, 'entidad_razon_social') and proyecto.entidad_razon_social:
                # Fetch entidad for tipo_documento and numero_documento
                entidad_result = EntidadResult(
                    razon_social=proyecto.entidad_razon_social,
                    tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None) or "",
                    numero_documento=getattr(proyecto, 'entidad_numero_documento', None) or "",
                )
        
        # Build ProyectoResult
        proyecto = liquidacion_general.proyecto
        distrito_result = None
        if proyecto.distrito_id:
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
                            departamento=(
                                DepartamentoResult(
                                    id=str(distrito.provincia.departamento.id),
                                    nombre=distrito.provincia.departamento.nombre,
                                )
                                if distrito.provincia.departamento
                                else None
                            ),
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

        # Build ContactoResult (inline contacto principal, opcional)
        contacto_result = None
        if liquidacion_general.contacto:
            contacto = liquidacion_general.contacto
            contacto_result = ContactoResult(
                id=str(contacto.id),
                nombres=contacto.nombres,
                apellidos=contacto.apellidos,
                dni=contacto.dni,
                cargo=contacto.cargo,
                telefono=contacto.telefono,
                celular=contacto.celular,
                email=contacto.email,
            )

        return EdificacionesPrimeraRevisionResult(
            liquidacion_general=LiquidacionGeneralResult(
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
                fecha_registro=liquidacion_general.created_at.isoformat(),
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
                contacto=contacto_result,
                revisiones_previas=revisiones_previas,
                delegados=[],
                tipo_liquidacion=(
                    TipoLiquidacionResult(
                        codigo=liquidacion_general.tipo_liquidacion.codigo,
                        nombre=liquidacion_general.tipo_liquidacion.nombre,
                    )
                    if liquidacion_general.tipo_liquidacion
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionEspecificaEdificacionesResult(
                id=str(edificacion.id),
                numero=edificacion.numero,
            ),
            liquidacion_tipo=LiquidacionPorcentajeObraResult(
                id=str(liquidacion_po.id),
                liquidacion_general_id=str(liquidacion_po.liquidacion_general_id),
                tipo_tramite=liquidacion_po.tipo_tramite,  # NULL for now
                valor_declarado=liquidacion_po.valor_declarado,
                porcentaje_liquidacion=liquidacion_po.porcentaje_liquidacion,
                derecho_minimo=liquidacion_po.derecho_minimo,
                derecho_maximo=liquidacion_po.derecho_maximo,
                porcentaje_minimo_uit=liquidacion_po.porcentaje_minimo_uit,
                derecho_aplicado_id=str(liquidacion_po.derecho_aplicado_id),
                detalles=[
                    DetallePorcentajeObraResult(
                        id=str(d.id),
                        tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                        especialidad_id=str(d.especialidad_id),
                        porcentaje_aplicado=d.porcentaje_aplicado,
                        subtotal=d.subtotal,
                        igv=d.igv,
                        uit=d.uit,
                        total=d.total,
                    )
                    for d in liquidacion_po.detalles.all()
                ],
            ),
            revisiones_previas=[],
        )
