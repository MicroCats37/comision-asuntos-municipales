"""
LiquidacionPOBaseFlujo — base class for PorcentajeObra flows.

Provides the shared PO creation lifecycle (quote-first pattern):
1. Entidad (upsert)
2. Proyecto
3. Calculate PorcentajeObra cotizacion (pure arithmetic, no DB dependency)
4. Create LiquidacionGeneral with correct sub_total/total (no zero-fill)
5. Assign IGV/UIT FKs and usuario_creador (persisted in one save)
6. Create LiquidacionPorcentajeObra + detalles via core (abstract — subclass provides cotizacion)
7. Create type-specific PO wrapper (abstract)
8. Build result (abstract)

Subclasses must override:
- _get_tipo_liquidacion_code() → str (TipoLiquidacion enum value)
- _crear_wrapper(liquidacion_general) → wrapper instance
- _build_result(...) → LiquidacionEspecificaPrimeraRevisionResult
- _calcular_cotizacion(...) → cotizacion result (subclass decides params)

@transaction.atomic is on the template method (_ejecutar_primera_revision_sync).

NOTE: This base does NOT include nueva_revision — that is Edificaciones-specific
and lives in LiquidacionEdificacionesFlujo. Taludes and Impacto Vial do not
have nueva_revision.
"""
from abc import abstractmethod
from datetime import date
from decimal import Decimal
from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from injector import inject

from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.primera_revision_data import (
    LiquidacionEspecificaPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
    LiquidacionEspecificaPrimeraRevisionResult,
)


class LiquidacionPOBaseFlujo:
    """
    Base class for PO (PorcentajeObra) flows: Edificaciones, Taludes, Impacto Vial.

    Order of DB operations:
    1. Entidad (upsert) — shared
    2. Proyecto — shared
    3. LiquidacionGeneral (sub_total=0, total=0 initially) — shared
    4. Calculate PO cotizacion — abstract (subclass decides params)
    5. Set LiquidacionGeneral totals from cotizacion — shared
    6. Create LiquidacionPorcentajeObra + detalles — shared (uses abstract cotizacion)
    7. Create type-specific PO wrapper — abstract (Edificaciones/Taludes/ImpactoVial)
    8. Build result — abstract (subclass decides result shape)

    All in @transaction.atomic via the template method.
    """

    @inject
    def __init__(
        self,
        porcentaje_core: LiquidacionPorcentajeObraCoreService,
        general_core: LiquidacionGeneralCoreService,
        relacion_core: LiquidacionRelacionCoreService,
    ):
        self.porcentaje_core = porcentaje_core
        self.general_core = general_core
        self.relacion_core = relacion_core

    # ── Template Method ───────────────────────────────────────────────────────

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

        # Step 1: Entidad (shared — identical across all PO types)
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto (shared)
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Resolve IGV/UIT upfront (no DB dependency on LG creation).
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Step 4: Resolve contacto if present (convert Pydantic schema to ORM instance).
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.create_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Step 5: Calculate PO cotizacion BEFORE creating LiquidacionGeneral (quote-first pattern).
        # Cotizacion is pure arithmetic — no DB records needed.
        cotizacion = self._calcular_cotizacion(
            po_data=po_data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 6: Create LiquidacionGeneral with final totals and FKs already set (no zero-fill, no post-create save).
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
            contacto=contacto,
        )

        # Step 6: Create LiquidacionPorcentajeObra + detalles (shared)
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 7: Create type-specific PO wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 7.5: Create relation group and member for primera revision
        # Uses base class helper that derives relacion_key from _get_tipo_liquidacion_code + tipo_tramite
        self._crear_relacion_grupo_primera_revision(
            liquidacion_general=liquidacion_general,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 8: Build result (abstract)
        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=wrapper,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    def ejecutar_edge(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        numero_revision: int,
        cotizacion,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Execute edge (manual) PO flow — standalone, no relation group.

        Differences from _ejecutar_primera_revision_sync:
        - modo_calculo = MANUAL (explicit, not default TARIFA)
        - numero_revision is given explicitly by caller (not always 1)
        - No relation group creation (edge is standalone)
        - Uses create_liquidacion_porcentaje_obra_edge (no tarifa, no derecho)
        - cotizacion is pre-computed by orchestrator via calcular_cotizacion_po_edge

        All in @transaction.atomic.
        """
        return self._ejecutar_edge_sync(
            usuario_id=usuario_id,
            data=data,
            igv_porcentaje=igv_porcentaje,
            numero_revision=numero_revision,
            cotizacion=cotizacion,
        )

    @transaction.atomic()
    def _ejecutar_edge_sync(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        numero_revision: int,
        cotizacion,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Step 1: Entidad (shared)
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto (shared)
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Fetch IGV/UIT upfront (no DB dependency on LG creation)
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()

        # Step 4: Create LiquidacionGeneral with correct totals and modo_calculo (quote-first pattern).
        # Cotizacion is pre-computed by orchestrator — no DB dependency.
        from modules.liquidaciones.domain.constants import ModoCalculoLiquidacion

        tipo_liquidacion = TipoLiquidacionModel.objects.get(codigo=self._get_tipo_liquidacion_code())
        liquidacion_general = self._crear_liquidacion_general(
            gen_data=gen_data,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
            modo_calculo=ModoCalculoLiquidacion.MANUAL,
        )

        # Step 6: Create LiquidacionPorcentajeObra + detalles (edge variant — no tarifa, no derecho)
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra_edge(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            tipo_tramite=None,  # edge does not use tipo_tramite
        )

        # Step 7: Create type-specific PO wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # NOTE: No relation group creation for edge (standalone, not linked to other liquidations)

        # Step 8: Build result (abstract)
        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=wrapper,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    # ── Legacy support (shared structure across all PO types) ─────────────────

    @transaction.atomic()
    def _ejecutar_legacy_sync(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        numero_revision: int,
        fecha_registro: date,
        legacy_visitas_core,  # LiquidacionLegacyPorVisitasCoreService
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Shared legacy first revision skeleton.
        Subclass overrides _crear_liquidacion_general to add type-specific fields
        (e.g. retencion for Edificaciones).
        """
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Step 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Resolve IGV/UIT via legacy core (no DB dependency on LG creation)
        igv = legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = legacy_visitas_core.get_uit_por_fecha(fecha_registro)

        # Step 4: Calculate PO cotizacion (uses override_subtotal if set by ejecutar_legacy)
        cotizacion = self._calcular_cotizacion(
            po_data=po_data,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 5: Create LiquidacionGeneral with correct totals and FKs in one shot (quote-first pattern).
        tipo_liquidacion = TipoLiquidacionModel.objects.get(codigo=self._get_tipo_liquidacion_code())
        liquidacion_general = self._crear_liquidacion_general(
            gen_data=gen_data,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            sub_total=cotizacion.total_subtotal,
            total=cotizacion.total,
            fecha_registro=fecha_registro,
            igv_id=igv,
            uit_id=uit,
            usuario_creador_id=usuario_id,
            legacy=True,
        )

        # Step 7: Create LiquidacionPorcentajeObra + detalles
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
            tipo_tramite=po_data.tipo_tramite,
        )

        # Step 8: Wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 9: Result (abstract)
        return self._build_result(
            liquidacion_general=liquidacion_general,
            wrapper=wrapper,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    def _get_tipo_liquidacion_code(self) -> str:
        """
        Return the TipoLiquidacion enum value for this flow.
        E.g. TipoLiquidacion.EDIFICACION, TipoLiquidacion.TALUDES, TipoLiquidacion.IMPACTO_VIAL
        """
        raise NotImplementedError

    @abstractmethod
    def _crear_wrapper(self, liquidacion_general) -> object:
        """
        Create the type-specific PO wrapper (Edificacion/Taludes/ImpactoVial).
        The wrapper is an identity model with a OneToOne FK to LiquidacionGeneral.
        """
        raise NotImplementedError

    @abstractmethod
    def _build_result(
        self,
        liquidacion_general,
        wrapper,
        liquidacion_po,
        usuario_id: int,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Build the LiquidacionEspecificaPrimeraRevisionResult from ORM objects.
        Must be implemented by each concrete flow since result shapes may vary.
        """
        raise NotImplementedError

    @abstractmethod
    def _calcular_cotizacion(
        self,
        po_data,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ):
        """
        Calculate PO cotizacion via porcentaje_core.
        Returns cotizacion object with total_subtotal and total.
        Subclasses may pass override_subtotal for legacy flows.
        """
        raise NotImplementedError

    # ── Hooks (optional override) ─────────────────────────────────────────────

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
        descripcion_legacy: Optional[str] = None,
        legacy: bool = False,
    ) -> object:
        """
        Create LiquidacionGeneral record.

        Default implementation handles the common fields present in all PO flows.
        Subclasses may override to add type-specific fields (e.g. Edificaciones
        adds retencion).

        Pass sub_total and total for quote-first creation (avoids zero-fill pattern).
        The default creates with numero_revision=1 (primera revision).
        For legacy flows, pass numero_revision explicitly.
        FKs (igv_id, uit_id, usuario_creador_id), fecha_registro, modo_calculo,
        contacto, and descripcion_legacy are forwarded to create_liquidacion_general when provided.
        """
        return self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
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

    # ── Relation Group Helpers (reusable across PO flows) ─────────────────────────

    def _crear_relacion_grupo_primera_revision(
        self,
        liquidacion_general,
        tipo_tramite: str | None = None,
    ) -> tuple:
        """
        Create a new relation group and add the liquidacion as its first member.

        Use this for primera revision (relacionada) — creates a new group
        and adds the liquidacion with numero_revision=1.

        Args:
            liquidacion_general: the LiquidacionGeneral instance (already saved)
            tipo_tramite: optional tramite type for EDIFICACION subclass to
                         derive the correct relation_key (e.g. OBRA_NUEVA → EDIFICACION-OBRA)

        Returns:
            tuple: (grupo, miembro)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
            tipo_tramite=tipo_tramite,
        )
        return self.relacion_core.crear_grupo_con_miembro(
            liquidacion=liquidacion_general,
            relacion_key=relacion_key,
            numero_revision=liquidacion_general.numero_revision,
        )

    def _calcular_siguiente_numero_revision(
        self,
        liquidacion_previa,
    ) -> int:
        """
        Calculate the next revision number given a previous liquidacion.

        Revision sequence is: 1 → 3 → 5 (odd numbers, +2 increment).
        Returns liquidacion_previa.numero_revision + 2.

        Args:
            liquidacion_previa: the previous LiquidacionGeneral

        Returns:
            int: the next revision number (e.g. 1 → 3, 3 → 5)
        """
        return liquidacion_previa.numero_revision + 2

    def _crear_relacion_grupo_nueva_revision(
        self,
        liquidacion_previa,
        liquidacion_general,
        tipo_tramite: str | None = None,
    ) -> tuple:
        """
        Add a liquidacion to the relation group of a previous liquidacion.

        Use this for nueva revision — finds the group of liquidacion_previa
        (or creates one if previa has no group yet) and adds the new liquidacion
        as a member with the next revision number.

        Args:
            liquidacion_previa: the existing LiquidacionGeneral this revision is based on
            liquidacion_general: the new LiquidacionGeneral instance (already saved)
            tipo_tramite: optional tramite type for EDIFICACION subclass

        Returns:
            tuple: (miembro_nuevo, fue_backfill)
                - miembro_nuevo: the created member for the new liquidacion
                - fue_backfill: True if a backfill was performed (previa had no group)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
            tipo_tramite=tipo_tramite,
        )
        numero_revision = self._calcular_siguiente_numero_revision(liquidacion_previa)
        return self.relacion_core.agregar_miembro_a_grupo_de_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_nueva=liquidacion_general,
            relacion_key=relacion_key,
            numero_revision=numero_revision,
        )

    def _crear_relacion_grupo_desde_previa(
        self,
        liquidacion_previa,
        liquidacion_general,
        tipo_tramite: str | None = None,
    ) -> tuple:
        """
        Add a liquidacion to the relation group of a previous liquidacion,
        with numero_revision=1.

        Use this for /relacionada endpoint — creates a new liquidacion with
        numero_revision=1 that is related to an existing liquidacion (which may
        have numero_revision=1 or higher). Finds the group of liquidacion_previa
        (or creates one if previa has no group yet) and adds the new liquidacion
        as a member with numero_revision=1.

        Args:
            liquidacion_previa: the existing LiquidacionGeneral this is related to
            liquidacion_general: the new LiquidacionGeneral instance (already saved)
            tipo_tramite: optional tramite type for EDIFICACION subclass

        Returns:
            tuple: (miembro_nuevo, fue_backfill)
                - miembro_nuevo: the created member for the new liquidacion
                - fue_backfill: True if a backfill was performed (previa had no group)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
            tipo_tramite=tipo_tramite,
        )
        tipo_tramite_previa = None
        try:
            tipo_tramite_previa = liquidacion_previa.liquidacion_porcentaje_obra.tipo_tramite
        except ObjectDoesNotExist:
            tipo_tramite_previa = None

        relacion_key_previa = generar_relacion_key(
            tipo_liquidacion=liquidacion_previa.tipo_liquidacion.codigo,
            tipo_tramite=tipo_tramite_previa,
        )
        # numero_revision=1 for /relacionada (new liquidacion is always revision 1)
        return self.relacion_core.agregar_miembro_a_grupo_de_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_nueva=liquidacion_general,
            relacion_key=relacion_key,
            numero_revision=1,
            relacion_key_previa=relacion_key_previa,
        )
