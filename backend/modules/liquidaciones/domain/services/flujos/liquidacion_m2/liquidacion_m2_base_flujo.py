"""
LiquidacionM2FlujoBase — base class for M2 (Metro Cuadrado) flows.

Provides the shared M2 creation lifecycle for HU and MS:
1. Entidad upsert (shared)
2. Proyecto creation (shared)
3. LiquidacionGeneral with cotizacion totals, IGV/UIT FKs (shared)
4. LiquidacionPorMetroCuadrado creation via m2_core (shared)
5. Type-specific wrapper creation (abstract)
6. Result building (abstract)

@transaction.atomic is on the template methods.

Subclasses must override:
- _get_tipo_liquidacion_code() → str (TipoLiquidacion.HABILITACION_URBANA | MECANICA_SUELOS)
- _crear_wrapper(liquidacion_general) → wrapper ORM instance
- _build_result(...) → type-specific PrimeraRevisionResult
- _build_result_legacy(...) → type-specific PrimeraRevisionResult
"""
from abc import abstractmethod
from datetime import date
from decimal import Decimal
from django.db import transaction
from injector import inject

from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
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
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.constants import ModoCalculoLiquidacion


class LiquidacionM2FlujoBase:
    """
    Base class for M2 flows: Habilitación Urbana and Mecánica de Suelos.

    Order of DB operations:
    1. Entidad upsert — shared
    2. Proyecto — shared
    3. LiquidacionGeneral (sub_total/total from cotizacion, IGV/UIT FKs) — shared
    4. LiquidacionPorMetroCuadrado via m2_core — shared
    5. Type-specific wrapper — abstract
    6. Result building — abstract

    All in @transaction.atomic via the template methods.
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        m2_core: LiquidacionPorMetroCuadradoCoreService,
        relacion_core: LiquidacionRelacionCoreService,
    ):
        self.general_core = general_core
        self.m2_core = m2_core
        self.relacion_core = relacion_core

    # ── Template Method: Primera Revisión ─────────────────────────────────────

    def _ejecutar_primera_revision_base(
        self,
        usuario_id: int,
        gen_data,
        esp_data,
        cotizacion,
    ):
        """
        Shared primera revisión steps for M2 flows.
        Subclass calls this from its transactional method.
        """
        # Step 1: Entidad upsert (shared — identical for HU and MS)
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto (shared)
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "urbanizacion": gen_data.proyecto.urbanizacion,
            "entidad_razon_social": getattr(
                gen_data.proyecto,
                "entidad_razon_social",
                getattr(gen_data.proyecto.entidad, "razon_social", None),
            ),
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: LiquidacionGeneral with cotizacion totals + vigentes FKs
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        tipo_liquidacion = TipoLiquidacionModel.objects.get(
            codigo=self._get_tipo_liquidacion_code()
        )
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=1,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
            sub_total=Decimal(str(cotizacion.subtotal)),
            total=Decimal(str(cotizacion.total)),
            igv_id=igv_vigente if igv_vigente else None,
            uit_id=uit_vigente if uit_vigente else None,
            usuario_creador_id=usuario_id,
        )

        # Step 4: LiquidacionPorMetroCuadrado via m2_core (shared)
        derecho = self.m2_core.get_derecho_minimo_m2_vigente()
        tarifa = self.m2_core.get_tarifa_m2_vigente(self._get_tipo_liquidacion_code())
        liquidacion_m2 = self.m2_core.create_liquidacion_por_metro_cuadrado(
            liquidacion_general=liquidacion_general,
            area_solicitada=float(esp_data.datos.area_solicitada),
            tarifa_aplicada=tarifa,
            derecho_aplicado=derecho,
            subtotal=liquidacion_general.sub_total,
            total=liquidacion_general.total,
        )

        # Step 5: Type-specific wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 5.5: Create relation group and member for primera revision
        # Uses base class helper that derives relacion_key from _get_tipo_liquidacion_code
        self._crear_relacion_grupo_primera_revision(liquidacion_general=liquidacion_general)

        # Step 6: Result building (abstract)
        return self._build_result(
            liquidacion_general=liquidacion_general,
            liquidacion_m2=liquidacion_m2,
            wrapper=wrapper,
            derecho=derecho,
            usuario_id=usuario_id,
        )

    # ── Template Method: Legacy ───────────────────────────────────────────────

    def ejecutar_edge(
        self,
        usuario_id: int,
        gen_data,
        area_m2,
        subtotal_manual,
        igv_porcentaje: Decimal,
        numero_revision: int,
    ):
        """
        Shared manual/edge M2 flow.

        Edge liquidaciones are standalone manual records: they do not create a
        relation group and use the cotizacion already calculated by the
        orchestrator.
        """
        return self._ejecutar_edge_sync(
            usuario_id=usuario_id,
            gen_data=gen_data,
            area_m2=area_m2,
            subtotal_manual=subtotal_manual,
            igv_porcentaje=igv_porcentaje,
            numero_revision=numero_revision,
        )

    @transaction.atomic()
    def _ejecutar_edge_sync(
        self,
        usuario_id: int,
        gen_data,
        area_m2,
        subtotal_manual,
        igv_porcentaje: Decimal,
        numero_revision: int,
    ):
        # Step 1: Entidad upsert (shared — identical for HU and MS)
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto (shared)
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "urbanizacion": gen_data.proyecto.urbanizacion,
            "entidad_razon_social": getattr(
                gen_data.proyecto,
                "entidad_razon_social",
                getattr(gen_data.proyecto.entidad, "razon_social", None),
            ),
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        subtotal = Decimal(str(subtotal_manual))
        total = subtotal + (subtotal * Decimal(str(igv_porcentaje)))

        # Step 3: LiquidacionGeneral with manual-mode cotizacion totals
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        tipo_liquidacion = TipoLiquidacionModel.objects.get(
            codigo=self._get_tipo_liquidacion_code()
        )
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
            sub_total=subtotal,
            total=total,
            igv_id=igv_vigente if igv_vigente else None,
            uit_id=uit_vigente if uit_vigente else None,
            usuario_creador_id=usuario_id,
            modo_calculo=ModoCalculoLiquidacion.MANUAL,
        )

        # Step 4: LiquidacionPorMetroCuadrado via m2_core (edge/manual)
        liquidacion_m2 = self.m2_core.create_liquidacion_por_metro_cuadrado_edge(
            liquidacion_general=liquidacion_general,
            area_solicitada=float(area_m2),
            subtotal=subtotal,
            total=total,
        )

        # Step 5: Type-specific wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general)

        # NOTE: No relation group creation for edge (standalone/manual record).
        return self._build_result(
            liquidacion_general=liquidacion_general,
            liquidacion_m2=liquidacion_m2,
            wrapper=wrapper,
            derecho=None,
            usuario_id=usuario_id,
        )

    # ── Template Method: Legacy ───────────────────────────────────────────────

    def _ejecutar_legacy_base(
        self,
        usuario_id: int,
        gen_data,
        esp_data,
        cotizacion,
        igv,
        uit,
        numero_revision: int,
        fecha_registro: date,
        numero: int | None = None,
    ):
        """
        Shared legacy first revision steps for M2 flows.
        Mirrors _ejecutar_primera_revision_base but:
        - Uses passed igv/uit ORM objects for FKs on liquidacion_general
        - Uses cotizacion.derecho_id/tarifa_id (pre-resolved by orchestrator)
        - Sets explicit fecha_registro, numero_revision, descripcion_legacy
        """
        # Step 1: Entidad upsert (shared)
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto (shared — urbanizacion comes from schema)
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "urbanizacion": getattr(gen_data.proyecto, "urbanizacion", None),
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: LiquidacionGeneral with cotizacion totals + passed igv/uit
        tipo_liquidacion = TipoLiquidacionModel.objects.get(
            codigo=self._get_tipo_liquidacion_code()
        )
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
            descripcion_legacy=getattr(gen_data, 'descripcion_legacy', None),
            sub_total=Decimal(str(cotizacion.subtotal)),
            total=Decimal(str(cotizacion.total)),
            igv_id=igv if igv else None,
            uit_id=uit if uit else None,
            usuario_creador_id=usuario_id,
            fecha_registro=fecha_registro,
        )

        # Step 4: LiquidacionPorMetroCuadrado via m2_core with pre-resolved derecho/tarifa
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            DerechoPorMetroCuadrado,
            TarifaPorMetroCuadrado,
        )
        derecho = DerechoPorMetroCuadrado.objects.get(id=cotizacion.derecho_id)
        tarifa = TarifaPorMetroCuadrado.objects.get(id=cotizacion.tarifa_id)
        liquidacion_m2 = self.m2_core.create_liquidacion_por_metro_cuadrado(
            liquidacion_general=liquidacion_general,
            area_solicitada=float(esp_data.datos.area_solicitada),
            tarifa_aplicada=tarifa,
            derecho_aplicado=derecho,
            subtotal=liquidacion_general.sub_total,
            total=liquidacion_general.total,
        )

        # Step 5: Type-specific wrapper (abstract)
        wrapper = self._crear_wrapper(liquidacion_general, numero=numero)

        # Step 6: Result building (abstract)
        return self._build_result_legacy(
            liquidacion_general=liquidacion_general,
            liquidacion_m2=liquidacion_m2,
            wrapper=wrapper,
            derecho=derecho,
            usuario_id=usuario_id,
        )

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    def _get_tipo_liquidacion_code(self) -> str:
        """
        Return the TipoLiquidacion enum value for this flow.
        E.g. TipoLiquidacion.HABILITACION_URBANA, TipoLiquidacion.MECANICA_SUELOS
        """
        raise NotImplementedError

    @abstractmethod
    def _crear_wrapper(self, liquidacion_general, numero: int | None = None) -> object:
        """
        Create the type-specific M2 wrapper (HU or MS).
        The wrapper is an identity model with a OneToOne FK to LiquidacionGeneral.
        When numero is provided (non-None), it is passed to the wrapper constructor
        to preserve the historical legacy numero instead of auto-generating.
        """
        raise NotImplementedError

    @abstractmethod
    def _build_result(
        self,
        liquidacion_general,
        liquidacion_m2,
        wrapper,
        derecho,
        usuario_id: int,
    ):
        """
        Build the type-specific PrimeraRevisionResult from ORM objects.
        Must be implemented by each concrete flow.
        """
        raise NotImplementedError

    @abstractmethod
    def _build_result_legacy(
        self,
        liquidacion_general,
        liquidacion_m2,
        wrapper,
        derecho,
        usuario_id: int,
    ):
        """
        Build the type-specific PrimeraRevisionResult for legacy flows.
        Must be implemented by each concrete flow.
        """
        raise NotImplementedError

    # ── Relation Group Helpers (reusable across M2 flows) ─────────────────────────

    def _crear_relacion_grupo_primera_revision(
        self,
        liquidacion_general,
    ) -> tuple:
        """
        Create a new relation group and add the liquidacion as its first member.

        Use this for primera revision (relacionada) — creates a new group
        and adds the liquidacion with numero_revision=1.

        For M2 flows (HU/MS), no tipo_tramite is needed — they use fixed type codes.

        Args:
            liquidacion_general: the LiquidacionGeneral instance (already saved)

        Returns:
            tuple: (grupo, miembro)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
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
    ) -> tuple:
        """
        Add a liquidacion to the relation group of a previous liquidacion.

        Use this for nueva revision — finds the group of liquidacion_previa
        (or creates one if previa has no group yet) and adds the new liquidacion
        as a member with the next revision number.

        For M2 flows (HU/MS), no tipo_tramite is needed — they use fixed type codes.

        Args:
            liquidacion_previa: the existing LiquidacionGeneral this revision is based on
            liquidacion_general: the new LiquidacionGeneral instance (already saved)

        Returns:
            tuple: (miembro_nuevo, fue_backfill)
                - miembro_nuevo: the created member for the new liquidacion
                - fue_backfill: True if a backfill was performed (previa had no group)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
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
    ) -> tuple:
        """
        Add a liquidacion to the relation group of a previous liquidacion,
        with numero_revision=1.

        Use this for /relacionada endpoint — creates a new liquidacion with
        numero_revision=1 that is related to an existing liquidacion. Finds the
        group of liquidacion_previa (or creates one if previa has no group yet)
        and adds the new liquidacion as a member with numero_revision=1.

        For M2 flows (HU/MS), no tipo_tramite is needed — they use fixed type codes.

        Args:
            liquidacion_previa: the existing LiquidacionGeneral this is related to
            liquidacion_general: the new LiquidacionGeneral instance (already saved)

        Returns:
            tuple: (miembro_nuevo, fue_backfill)
                - miembro_nuevo: the created member for the new liquidacion
                - fue_backfill: True if a backfill was performed (previa had no group)
        """
        relacion_key = generar_relacion_key(
            tipo_liquidacion=self._get_tipo_liquidacion_code(),
        )
        return self.relacion_core.agregar_miembro_a_grupo_de_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_nueva=liquidacion_general,
            relacion_key=relacion_key,
            numero_revision=1,
        )
