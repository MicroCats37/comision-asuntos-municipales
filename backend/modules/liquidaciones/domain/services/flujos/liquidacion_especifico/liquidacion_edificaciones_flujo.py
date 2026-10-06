"""
LiquidacionEdificacionesFlujo — refactored to inherit from LiquidacionPOBaseFlujo.

S2: Extracted shared PO lifecycle to LiquidacionPOBaseFlujo.
Only type-specific overrides remain: _get_tipo_liquidacion_code, _calcular_cotizacion,
_crear_wrapper, _build_result.

Contacto handling: Edificaciones creates contacto inline (step 2.5) which is
injected into _crear_liquidacion_general override.

nueva_revision: Edificaciones-specific (no equivalent in other PO flows) —
kept as-is, does not use base template.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from django.db import IntegrityError, transaction
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
    LiquidacionPOBaseFlujo,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
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
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    LiquidacionPorcentajeObraResult,
    DetallePorcentajeObraResult,
    EspecialidadResult,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionEdificacionesFlujo(LiquidacionPOBaseFlujo):
    """
    Flujo for Edificaciones primera revision.

    Order of DB operations (inherited from base):
    1. Entidad (upsert) — shared
    2. Proyecto — shared
    3. Contacto + LiquidacionGeneral — Edificaciones override injects contacto
    4. Calculate PorcentajeObra — subclass override
    5. Set LiquidacionGeneral totals — shared
    6. Create LiquidacionPorcentajeObra + detalles — shared
    7. LiquidacionEdificacion wrapper — subclass override
    8. Build result — subclass override

    All in @transaction.atomic via base template method.

    NOTE: nueva_revision is Edificaciones-specific (different entity/project reuse
    and M2M liquidaciones_previas) — kept as concrete method, not in base.
    """

    # ── Type-specific overrides ───────────────────────────────────────────────

    def _get_tipo_liquidacion_code(self) -> str:
        return TipoLiquidacion.EDIFICACION

    def _calcular_cotizacion(
        self,
        po_data,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ):
        """
        Calculate PO cotizacion for Edificaciones.

        For legacy flows, checks self._override_subtotal and self._override_total
        (set by ejecutar_legacy before calling the base template).
        """
        kwargs = {}
        if getattr(self, '_override_subtotal', None) is not None:
            kwargs['override_subtotal'] = self._override_subtotal
        if getattr(self, '_override_total', None) is not None:
            kwargs['override_total'] = self._override_total

        return self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
            **kwargs,
        )

    def _crear_wrapper(self, liquidacion_general) -> LiquidacionEdificacion:
        """Create Edificacion identity wrapper."""
        return LiquidacionEdificacion.objects.create(
            liquidacion=liquidacion_general,
            numero=getattr(self, "_legacy_numero", None),
        )

    def _build_result(
        self,
        liquidacion_general,
        wrapper,
        liquidacion_po,
        usuario_id: int,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """Build result for Edificaciones."""
        liquidacion_general.refresh_from_db()

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

        # Build general result with delegados (Edificaciones-specific for primera revision)
        delegados = self.general_core.build_delegados_result(liquidacion_general)
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            delegados=delegados,
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=LiquidacionEspecificaResult(
                id=str(wrapper.id),
                numero=wrapper.numero,
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
                derecho_aplicado_id=str(liquidacion_po.derecho_aplicado_id) if liquidacion_po.derecho_aplicado_id else None,
                detalles=[
                    DetallePorcentajeObraResult(
                        id=str(d.id),
                        tarifa_aplicada_id=str(d.tarifa_aplicada_id) if d.tarifa_aplicada_id else None,
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
        )

    # ── Contacto + LG creation (Edificaciones-specific override) ─────────────────

    # ── Nueva Revision (Edificaciones-specific — not in base) ─────────────────

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

    # ── Relacionada (Edificaciones-specific — not in base) ─────────────────

    def ejecutar_relacionada(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Creates a new liquidacion with numero_revision=1 that is related to
        an existing Edificaciones liquidacion.

        Similar to primera_revision but instead of creating a new relation group,
        joins the existing liquidacion's group (or creates a new group if the
        previous liquidacion has no group yet).

        Key differences from primera_revision:
        - Links to liquidacion_previa via relation group
        - numero_revision=1 (same as primera_revision)

        Key differences from nueva_revision:
        - numero_revision is always 1 (not previa.numero_revision + 2)
        - Does not clone proyecto (creates new proyecto like primera_revision)
        """
        return self._ejecutar_relacionada_sync(
            usuario_id=usuario_id,
            data=data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
            liquidacion_previa=liquidacion_previa,
        )

    @transaction.atomic()
    def _ejecutar_relacionada_sync(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Internal sync method for ejecutar_relacionada.
        Creates a new Edificaciones liquidacion related to an existing one.
        """
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Step 1: Entidad (upsert) — same as primera_revision
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto — same as primera_revision
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Contacto principal — same as primera_revision
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.create_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Step 4: Calculate PO cotizacion (pure arithmetic — no DB dependency)
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 5: Get IGV/UIT FKs (no DB dependency on LG creation)
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Step 6: LiquidacionGeneral with correct totals and FKs in one shot (quote-first pattern).
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.EDIFICACION),
            numero_revision=1,  # Always revision 1 for /relacionada
            retencion=gen_data.retencion,
            contacto=contacto,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
        )

        # Step 8: Create LiquidacionPorcentajeObra + detalles — same as primera_revision
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 9: LiquidacionEdificacion (identity wrapper) — same as primera_revision
        edificacion = LiquidacionEdificacion.objects.create(
            liquidacion=liquidacion_general
        )

        # Step 10: Create relation group link to previous liquidacion.
        # Uses _crear_relacion_grupo_desde_previa (numero_revision=1)
        # instead of _crear_relacion_grupo_primera_revision (also numero_revision=1
        # but creates a new group).
        self._crear_relacion_grupo_desde_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
            tipo_tramite=po_data.tipo_tramite,
        )

        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=edificacion,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
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

        # Entidad and Proyecto already exist — clone proyecto to isolate revision
        proyecto = self.general_core.clone_proyecto_for_liquidacion(liquidacion_previa)
        entidad = proyecto.entidad

        # Contacto upsert by ALL fields
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.upsert_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Calculate new numero_revision
        nueva_revision_numero = liquidacion_previa.numero_revision + 2

        # Get IGV/UIT FKs for snapshot (no DB dependency on LG creation)
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Calculate PorcentajeObra cotizacion (pure arithmetic — no DB dependency)
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # LiquidacionGeneral with correct totals and FKs in one shot (quote-first pattern).
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
            denominacion_de_proyecto=gen_data.denominacion_de_proyecto,
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
        )

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

        # Relation group: find or create group from liquidacion_previa and add new member.
        # Backfill scenario: if previa has no group yet, a new group is created and
        # previa is added as its first member before the new liquidacion is added.
        # Uses base class helper that derives relacion_key from _get_tipo_liquidacion_code + tipo_tramite.
        self._crear_relacion_grupo_nueva_revision(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
            tipo_tramite=po_data.tipo_tramite,
        )

        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=edificacion,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    # ── Legacy support ──────────────────────────────────────────────────────

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

        Stores override_subtotal and override_total on self so _calcular_cotizacion
        override picks them up when the base template calls it.
        """
        # Store override values so _calcular_cotizacion override can forward them
        po_data = data.liquidacion_especifica
        self._override_subtotal = getattr(po_data, 'override_subtotal', None)
        self._override_total = getattr(po_data, 'override_total', None)
        self._legacy_numero = numero

        try:
            return self._ejecutar_legacy_sync(
                usuario_id=usuario_id,
                data=data,
                igv_porcentaje=igv_porcentaje,
                derecho=derecho,
                uit_valor=uit_valor,
                numero_revision=numero_revision,
                fecha_registro=fecha_registro,
                legacy_visitas_core=legacy_visitas_core,
            )
        finally:
            # Clean up to avoid leaking state between calls
            self._override_subtotal = None
            self._override_total = None
            self._legacy_numero = None

    def _crear_liquidacion_general(
        self,
        gen_data,
        proyecto,
        tipo_liquidacion,
        numero_revision: int = 1,
        sub_total: Optional[Decimal] = None,
        total: Optional[Decimal] = None,
        igv_id=None,
        uit_id=None,
        usuario_creador_id=None,
        fecha_registro=None,
        modo_calculo=None,
        contacto=None,
        legacy: bool = False,
    ):
        """
        Override for Edificaciones to handle descripcion_legacy (from ejecutar_legacy path).

        Thin pass-through to parent for FKs, totals, contacto, and descripcion_legacy —
        all set in one shot at creation time.
        """
        descripcion_legacy = getattr(gen_data, 'descripcion_legacy', None)
        return super()._crear_liquidacion_general(
            gen_data=gen_data,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            sub_total=sub_total,
            total=total,
            igv_id=igv_id,
            uit_id=uit_id,
            usuario_creador_id=usuario_creador_id,
            fecha_registro=fecha_registro,
            modo_calculo=modo_calculo,
            contacto=contacto,
            descripcion_legacy=descripcion_legacy,
            legacy=legacy,
        )
