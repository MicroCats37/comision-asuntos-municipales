"""
LiquidacionHabilitacionUrbanaFlujo — M2 flow for Habilitación Urbana (Primera Revisión).

Inherits shared M2 lifecycle from LiquidacionM2FlujoBase.
Only the type-specific steps (wrapper creation, result building, tipo code) are overridden.
"""
from datetime import date
from decimal import Decimal
from django.db import transaction
from injector import inject

from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
    HabilitacionUrbanaPrimeraRevisionResult,
    LiquidacionEspecificaHabilitacionUrbanaResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
    LiquidacionM2Result,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.habilitacion_urbana_primera_revision_data import (
    HabilitacionUrbanaPrimeraRevisionData,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_m2.liquidacion_m2_base_flujo import (
    LiquidacionM2FlujoBase,
)


class LiquidacionHabilitacionUrbanaFlujo(LiquidacionM2FlujoBase):
    """
    Transactional flow for Habilitación Urbana (Primera Revisión).
    Delegates shared M2 lifecycle to LiquidacionM2FlujoBase.
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        m2_core: LiquidacionPorMetroCuadradoCoreService,
        relacion_core: LiquidacionRelacionCoreService,
    ):
        super().__init__(general_core=general_core, m2_core=m2_core, relacion_core=relacion_core)

    # ── Public entry points ──────────────────────────────────────────────────

    def ejecutar_primera_revision(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data)

    def ejecutar_legacy(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
        igv,
        uit,
        numero_revision: int,
        fecha_registro: date,
        numero: int | None = None,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Legacy first revision for Habilitación Urbana using historical fecha_registro.
        Delegates to base class template method.
        Stores numero as _legacy_numero for use in _crear_wrapper.
        """
        self._legacy_numero = numero
        gen_data = data.liquidacion_general
        esp_data = data.liquidacion_especifica
        cotizacion = data.cotizacion

        try:
            return self._ejecutar_legacy_base(
                usuario_id=usuario_id,
                gen_data=gen_data,
                esp_data=esp_data,
                cotizacion=cotizacion,
                igv=igv,
                uit=uit,
                numero_revision=numero_revision,
                fecha_registro=fecha_registro,
                numero=numero,
            )
        finally:
            self._legacy_numero = None

    # ── Transactional internal ────────────────────────────────────────────────

    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        esp_data = data.liquidacion_especifica
        cotizacion = data.cotizacion

        return self._ejecutar_primera_revision_base(
            usuario_id=usuario_id,
            gen_data=gen_data,
            esp_data=esp_data,
            cotizacion=cotizacion,
        )

    # ── Relacionada (HU-specific) ───────────────────────────────────────────

    def ejecutar_relacionada(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
        liquidacion_previa,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Creates a new Habilitacion Urbana liquidacion with numero_revision=1
        that is related to an existing HU liquidacion.

        Similar to primera_revision but links to the previous liquidacion's
        relation group instead of creating a new one.
        """
        return self._ejecutar_relacionada_sync(usuario_id, data, liquidacion_previa)

    @transaction.atomic()
    def _ejecutar_relacionada_sync(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
        liquidacion_previa,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Internal transactional method for ejecutar_relacionada.
        """
        gen_data = data.liquidacion_general
        esp_data = data.liquidacion_especifica
        cotizacion = data.cotizacion

        # Step 1: Entidad upsert
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Step 2: Proyecto — same as primera_revision
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "urbanizacion": gen_data.proyecto.urbanizacion,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Step 3: Contacto
        contacto = None
        if gen_data.contacto:
            from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import ContactoData
            contacto = self.general_core.create_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Step 4: LiquidacionGeneral with numero_revision=1
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
            contacto=contacto,
            sub_total=Decimal(str(cotizacion.subtotal)),
            total=Decimal(str(cotizacion.total)),
            igv_id=igv_vigente if igv_vigente else None,
            uit_id=uit_vigente if uit_vigente else None,
            usuario_creador_id=usuario_id,
        )

        # Step 6: LiquidacionM2 via m2_core
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

        # Step 7: HU wrapper
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 8: Create relation group link to previous liquidacion (numero_revision=1)
        self._crear_relacion_grupo_desde_previa(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
        )

        return self._build_result(
            liquidacion_general=liquidacion_general,
            liquidacion_m2=liquidacion_m2,
            wrapper=wrapper,
            derecho=derecho,
            usuario_id=usuario_id,
        )

    # ── Nueva Revision (HU-specific) ───────────────────────────────────────

    def ejecutar_nueva_revision(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
        liquidacion_previa,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        """
        Creates a new Habilitacion Urbana liquidacion with next odd revision number
        (e.g. 1 → 3, 3 → 5) based on an existing HU liquidacion.

        Reuses the proyecto from the previous liquidacion (cloned for isolation).
        """
        return self._ejecutar_nueva_revision_sync(usuario_id, data, liquidacion_previa)

    @transaction.atomic()
    def _ejecutar_nueva_revision_sync(
        self,
        usuario_id: int,
        data: HabilitacionUrbanaPrimeraRevisionData,
        liquidacion_previa,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        esp_data = data.liquidacion_especifica
        cotizacion = data.cotizacion

        # Step 1: Clone proyecto from previous liquidacion for revision isolation
        proyecto = self.general_core.clone_proyecto_for_liquidacion(liquidacion_previa)

        # Step 2: Contacto upsert
        contacto = None
        if gen_data.contacto:
            from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import ContactoData
            contacto = self.general_core.upsert_contacto(
                gen_data.contacto.model_dump() if hasattr(gen_data.contacto, "model_dump") else gen_data.contacto.__dict__
            )

        # Step 3: Calculate new numero_revision
        nueva_revision_numero = self._calcular_siguiente_numero_revision(liquidacion_previa)

        # Step 4: LiquidacionGeneral
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        tipo_liquidacion = TipoLiquidacionModel.objects.get(
            codigo=self._get_tipo_liquidacion_code()
        )
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(liquidacion_previa.municipalidad_id),
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=nueva_revision_numero,
            denominacion_de_proyecto=getattr(gen_data, 'denominacion_de_proyecto', None),
            contacto=contacto,
            sub_total=Decimal(str(cotizacion.subtotal)),
            total=Decimal(str(cotizacion.total)),
            igv_id=igv_vigente if igv_vigente else None,
            uit_id=uit_vigente if uit_vigente else None,
            usuario_creador_id=usuario_id,
        )

        # Step 6: LiquidacionM2 via m2_core
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

        # Step 7: HU wrapper
        wrapper = self._crear_wrapper(liquidacion_general)

        # Step 8: Create relation group link to previous liquidacion
        self._crear_relacion_grupo_nueva_revision(
            liquidacion_previa=liquidacion_previa,
            liquidacion_general=liquidacion_general,
        )

        return self._build_result(
            liquidacion_general=liquidacion_general,
            liquidacion_m2=liquidacion_m2,
            wrapper=wrapper,
            derecho=derecho,
            usuario_id=usuario_id,
        )

    # ── Abstract overrides ────────────────────────────────────────────────────

    def _get_tipo_liquidacion_code(self) -> str:
        return TipoLiquidacion.HABILITACION_URBANA

    def _crear_wrapper(self, liquidacion_general, numero: int | None = None) -> LiquidacionHabilitacionUrbana:
        return LiquidacionHabilitacionUrbana.objects.create(
            liquidacion=liquidacion_general,
            numero=numero,
        )

    def _build_result(
        self,
        liquidacion_general,
        liquidacion_m2,
        wrapper,
        derecho,
        usuario_id: int,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        # Build ContactoResult (inline — HU-specific contact may differ in future)
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

        # Explicitly resolve delegados (M2 liquidations support delegados in all cases except IO)
        delegados = self.general_core.build_delegados_result(liquidacion_general)

        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            delegados=delegados,
        )

        tipo_result = LiquidacionM2Result(
            id=str(liquidacion_m2.id),
            area_m2=liquidacion_m2.area_m2,
            costo_por_m2=liquidacion_m2.costo_por_m2,
            derecho_minimo=liquidacion_m2.derecho_minimo,
            derecho_maximo=liquidacion_m2.derecho_maximo if liquidacion_m2.derecho_maximo else None,
            derecho_aplicado_id=str(derecho.id) if derecho else None,
            tarifa_aplicada_id=str(liquidacion_m2.tarifa_aplicada_id) if liquidacion_m2.tarifa_aplicada_id else None,
        )

        especifica_result = LiquidacionEspecificaHabilitacionUrbanaResult(
            id=str(wrapper.id),
            numero=wrapper.numero,
        )

        return HabilitacionUrbanaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_tipo=tipo_result,
            liquidacion_especifica=especifica_result,
        )

    def _build_result_legacy(
        self,
        liquidacion_general,
        liquidacion_m2,
        wrapper,
        derecho,
        usuario_id: int,
    ) -> HabilitacionUrbanaPrimeraRevisionResult:
        # Explicitly resolve delegados (M2 liquidations support delegados in all cases except IO)
        delegados = self.general_core.build_delegados_result(liquidacion_general)

        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            delegados=delegados,
        )

        tipo_result = LiquidacionM2Result(
            id=str(liquidacion_m2.id),
            area_m2=liquidacion_m2.area_m2,
            costo_por_m2=liquidacion_m2.costo_por_m2,
            derecho_minimo=liquidacion_m2.derecho_minimo,
            derecho_maximo=liquidacion_m2.derecho_maximo if liquidacion_m2.derecho_maximo else None,
            derecho_aplicado_id=str(derecho.id) if derecho else None,
            tarifa_aplicada_id=str(liquidacion_m2.tarifa_aplicada_id) if liquidacion_m2.tarifa_aplicada_id else None,
        )

        especifica_result = LiquidacionEspecificaHabilitacionUrbanaResult(
            id=str(wrapper.id),
            numero=wrapper.numero,
        )

        return HabilitacionUrbanaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_tipo=tipo_result,
            liquidacion_especifica=especifica_result,
        )
