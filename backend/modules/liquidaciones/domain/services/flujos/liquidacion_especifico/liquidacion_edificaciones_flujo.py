"""
Flujo for Edificaciones (PorcentajeObra) first revision.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from datetime import date
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
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.primera_revision_data import (
    LiquidacionEspecificaPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
    LiquidacionEspecificaResult,
    LiquidacionEspecificaPrimeraRevisionResult,
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
    LiquidacionPreviaResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    LiquidacionPorcentajeObraResult,
    DetallePorcentajeObraResult,
    EspecialidadResult,
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
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data, igv_porcentaje, derecho, uit_valor)
    
    @transaction.atomic()
    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica
        
        # Paso 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )
        
        # Paso 2: Proyecto
        proyecto_data = {
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
              denominacion_de_proyecto=gen_data.denominacion_de_proyecto,
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
            tipo_tramite=po_data.tipo_tramite,
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
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
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
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
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
            tipo_tramite=po_data.tipo_tramite,
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
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Maps ORM objects to domain Result including revisiones_previas.
        Delegates common ORM→Result mapping to LiquidacionGeneralCoreService.
        """
        liquidacion_general.refresh_from_db()

        # Build previas list using the enriched helper (includes denominacion_de_proyecto, tipo, etc.)
        revisiones_previas = self.general_core.build_revisiones_previas_result(liquidacion_general)

        # Build ContactoResult inline (specific mapping not extracted to core)
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

        # Delegates: common mapping to core
        delegados = self.general_core.build_delegados_result(liquidacion_general)

        # Core: builds LiquidacionGeneralResult with all nested results
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            revisiones_previas=revisiones_previas,
            delegados=delegados,
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=LiquidacionEspecificaResult(
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
	                        especialidad=EspecialidadResult(
	                            id=str(d.especialidad_id),
	                            nombre=getattr(d.especialidad, 'nombre', '') or '',
	                        ) if d.especialidad_id else None,
	                        porcentaje_aplicado=d.porcentaje_aplicado,
	                        subtotal=d.subtotal,
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
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """Maps ORM objects to domain Result. Delegates common mapping to core."""
        liquidacion_general.refresh_from_db()

        # Build ContactoResult inline (specific mapping not extracted to core)
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

        # Core: builds LiquidacionGeneralResult (delegados para primera revision)
        delegados = self.general_core.build_delegados_result(liquidacion_general)
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            revisiones_previas=None,
            delegados=delegados,
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=LiquidacionEspecificaResult(
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
                        especialidad=EspecialidadResult(
                            id=str(d.especialidad_id),
                            nombre=getattr(d.especialidad, 'nombre', '') or '',
                        ) if d.especialidad_id else None,
                        porcentaje_aplicado=d.porcentaje_aplicado,
                        subtotal=d.subtotal,
                    )
                    for d in liquidacion_po.detalles.all()
                ],
            ),
            revisiones_previas=[],
        )

    @transaction.atomic()
    def ejecutar_legacy(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        numero_revision: int,
        fecha_registro: date,
        legacy_visitas_core: LiquidacionLegacyPorVisitasCoreService,
        numero: int | None = None,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Legacy first revision for Edificaciones using historical fecha_registro.

        Mirrors _ejecutar_primera_revision_sync but:
        - Uses passed igv_porcentaje/uit_valor for calculation (resolved by orchestrator)
        - Resolves igv/uit ORM objects via legacy_visitas_core for FKs on liquidacion_general
        - Sets explicit fecha_registro after create_liquidacion_general
        - Sets numero_revision from parameter (not hardcoded to 1)
        - Sets usuario_creador_id
        """
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Paso 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Paso 2: Proyecto
        proyecto_data = {
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
            contacto = self.general_core.upsert_contacto(
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
            numero_revision=numero_revision,
            contacto=contacto,
            denominacion_de_proyecto=gen_data.denominacion_de_proyecto,
            descripcion_legacy=gen_data.descripcion_legacy,
        )

        # Set historical fecha_registro (override default=timezone.now from model)
        liquidacion_general.fecha_registro = fecha_registro

        # Resolve IGV/UIT ORM objects for FK snapshot via legacy core
        igv = legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit
        liquidacion_general.usuario_creador_id = usuario_id

        # Paso 4: Calculate PorcentajeObra
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
            override_subtotal=po_data.override_subtotal,
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
            tipo_tramite=po_data.tipo_tramite,
        )

        # Paso 7: LiquidacionEdificacion (identity wrapper)
        edificacion = LiquidacionEdificacion(liquidacion=liquidacion_general)
        if numero is not None:
            edificacion.numero = numero
        else:
            # Legacy sin número histórico: se deja null (no autoincrementar).
            edificacion._skip_autonumero = True
        edificacion.save()

        # Build Result
        return self._build_result(
            liquidacion_general=liquidacion_general,
            edificacion=edificacion,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

