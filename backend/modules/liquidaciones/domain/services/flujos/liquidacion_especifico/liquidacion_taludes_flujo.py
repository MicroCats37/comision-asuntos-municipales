"""
LiquidacionTaludesFlujo — refactored to inherit from LiquidacionPOBaseFlujo.

S2: Extracted shared PO lifecycle to LiquidacionPOBaseFlujo.
Only type-specific overrides remain: _get_tipo_liquidacion_code, _calcular_cotizacion,
_crear_wrapper, _build_result.

Legacy flow: kept as concrete method (ejecutar_legacy) since it needs
descripcion_legacy which is type-specific.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from django.db import transaction
from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
    LiquidacionPOBaseFlujo,
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


class LiquidacionTaludesFlujo(LiquidacionPOBaseFlujo):
    """
    Flujo for Taludes primera revision.

    Order of DB operations (inherited from base):
    1. Entidad (upsert) — shared
    2. Proyecto — shared
    3. LiquidacionGeneral — shared
    4. Calculate PorcentajeObra — subclass override
    5. Set LiquidacionGeneral totals — shared
    6. Create LiquidacionPorcentajeObra + detalles — shared
    7. LiquidacionTaludes wrapper — subclass override
    8. Build result — subclass override

    All in @transaction.atomic via base template method.
    """

    # ── Type-specific overrides ───────────────────────────────────────────────

    def _get_tipo_liquidacion_code(self) -> str:
        return TipoLiquidacion.TALUDES

    def _calcular_cotizacion(
        self,
        po_data,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ):
        """
        Calculate PO cotizacion for Taludes.

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

    def _crear_wrapper(self, liquidacion_general) -> LiquidacionTaludes:
        """Create Taludes identity wrapper."""
        return LiquidacionTaludes.objects.create(liquidacion=liquidacion_general)

    def _build_result(
        self,
        liquidacion_general,
        wrapper,
        liquidacion_po,
        usuario_id: int,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """Build result for Taludes."""
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

        # Build general result with explicitly resolved delegados (PO can have delegados).
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
        legacy_visitas_core,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Legacy first revision for Taludes using historical fecha_registro.

        Stores override_subtotal and override_total on self so _calcular_cotizacion
        override picks them up when the base template calls it.
        """
        # Store override values so _calcular_cotizacion override can forward them
        po_data = data.liquidacion_especifica
        self._override_subtotal = getattr(po_data, 'override_subtotal', None)
        self._override_total = getattr(po_data, 'override_total', None)

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
        Override to add descripcion_legacy for Taludes.
        (descripcion_legacy is only set in legacy flows)

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

    # ── Nueva Revision (Taludes-specific) ────────────────────────────────────

    def ejecutar_nueva_revision(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        liquidacion_previa,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
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
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel

        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        proyecto = self.general_core.clone_proyecto_for_liquidacion(liquidacion_previa)

        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.upsert_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Calculate next revision number
        siguiente_revision = self._calcular_siguiente_numero_revision(liquidacion_previa)

        # Get IGV/UIT FKs upfront (no DB dependency on LG creation)
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Calculate cotizacion (pure arithmetic — no DB dependency)
        cotizacion = self._calcular_cotizacion(
            po_data=po_data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Create LiquidacionGeneral with correct totals and FKs in one shot (quote-first pattern).
        tipo_liquidacion = TipoLiquidacionModel.objects.get(codigo=self._get_tipo_liquidacion_code())
        liquidacion_general = self._crear_liquidacion_general(
            gen_data=gen_data,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=siguiente_revision,
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
            contacto=contacto,
        )

        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
            tipo_tramite=po_data.tipo_tramite,
        )
        wrapper = self._crear_wrapper(liquidacion_general)

        self._crear_relacion_grupo_nueva_revision(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
            tipo_tramite=po_data.tipo_tramite,
        )

        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=wrapper,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    # ── Relacionada (Taludes-specific) ──────────────────────────────────────────

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
        Creates a new Taludes liquidacion with numero_revision=1 that is related to
        an existing liquidacion.

        Same as primera_revision but at step 8.5 calls _crear_relacion_grupo_desde_previa
        instead of _crear_relacion_grupo_primera_revision to link to the previous liquidacion.
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
        Creates a new Taludes liquidacion related to an existing one.
        """
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel

        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Step 1: Entidad (upsert) — shared
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto — shared
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Calculate PO cotizacion (pure arithmetic — no DB dependency)
        cotizacion = self._calcular_cotizacion(
            po_data=po_data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 4: Get IGV/UIT FKs (no DB dependency on LG creation)
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Step 5: LiquidacionGeneral with correct totals and FKs in one shot (quote-first pattern).
        tipo_liquidacion = TipoLiquidacionModel.objects.get(codigo=self._get_tipo_liquidacion_code())
        liquidacion_general = self._crear_liquidacion_general(
            gen_data=gen_data,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
        )

        # Step 7: Create LiquidacionPorcentajeObra + detalles (shared)
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 8: Create type-specific PO wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 8.5: Create relation group link to previous liquidacion (NOT _crear_relacion_grupo_primera_revision)
        # Uses _crear_relacion_grupo_desde_previa which adds to previa's group with numero_revision=1
        self._crear_relacion_grupo_desde_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 9: Build result (abstract)
        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=wrapper,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )
