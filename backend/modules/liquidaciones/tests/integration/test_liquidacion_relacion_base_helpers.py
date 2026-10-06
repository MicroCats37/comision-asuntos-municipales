"""
Integration tests for PO and M2 base flujo relation helpers.

Tests the reusable helper methods added in Phase 2:
- LiquidacionPOBaseFlujo: _crear_relacion_grupo_primera_revision,
  _calcular_siguiente_numero_revision, _crear_relacion_grupo_nueva_revision
- LiquidacionM2FlujoBase: same helpers (no tipo_tramite variant)

These tests verify the helpers work correctly at the flujo level without
going through controller endpoints.

Fixtures: the test uses the actual flow classes with real DI services.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones


def _make_proyecto(ubigeo_distrito, seq):
    """Create a distinct Proyecto for each liquidation (OneToOne constraint)."""
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento=f"20{seq:08d}",
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario=f"Propietario Test {seq} SAC",
        direccion=f"Av. Test {seq}",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento=f"20{seq:08d}",
        entidad_razon_social=f"Propietario Test {seq} SAC",
    )


# ── LiquidacionPOBaseFlujo helper tests ────────────────────────────────────────

@pytest.mark.django_db
def test_po_base_calcular_siguiente_numero_revision_1_to_3(
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: a liquidacion with numero_revision=1
    WHEN: _calcular_siguiente_numero_revision is called
    THEN: it returns 3
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
        LiquidacionPOBaseFlujo,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
        LiquidacionPorcentajeObraCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcretePOBase(LiquidacionPOBaseFlujo):
        def _get_tipo_liquidacion_code(self):
            return "EDIFICACION"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _calcular_cotizacion(self, **kwargs):
            pass

    flujo = ConcretePOBase(
        porcentaje_core=LiquidacionPorcentajeObraCoreService(),
        general_core=LiquidacionGeneralCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    siguiente = flujo._calcular_siguiente_numero_revision(lg)
    assert siguiente == 3


@pytest.mark.django_db
def test_po_base_calcular_siguiente_numero_revision_3_to_5(
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: a liquidacion with numero_revision=3
    WHEN: _calcular_siguiente_numero_revision is called
    THEN: it returns 5
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
        LiquidacionPOBaseFlujo,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
        LiquidacionPorcentajeObraCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcretePOBase(LiquidacionPOBaseFlujo):
        def _get_tipo_liquidacion_code(self):
            return "EDIFICACION"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _calcular_cotizacion(self, **kwargs):
            pass

    flujo = ConcretePOBase(
        porcentaje_core=LiquidacionPorcentajeObraCoreService(),
        general_core=LiquidacionGeneralCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    siguiente = flujo._calcular_siguiente_numero_revision(lg)
    assert siguiente == 5


@pytest.mark.django_db
def test_po_base_crear_relacion_grupo_primera_revision_creates_group_and_member(
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: a saved LiquidacionGeneral with numero_revision=1
    WHEN: _crear_relacion_grupo_primera_revision is called with tipo_tramite=OBRA_NUEVA
    THEN: a new group is created with the liquidacion as member
          and relacion_key is EDIFICACION-OBRA
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
        LiquidacionPOBaseFlujo,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
        LiquidacionPorcentajeObraCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcretePOBase(LiquidacionPOBaseFlujo):
        def _get_tipo_liquidacion_code(self):
            return "EDIFICACION"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _calcular_cotizacion(self, **kwargs):
            pass

    flujo = ConcretePOBase(
        porcentaje_core=LiquidacionPorcentajeObraCoreService(),
        general_core=LiquidacionGeneralCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    grupo, miembro = flujo._crear_relacion_grupo_primera_revision(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
    )

    assert isinstance(grupo, LiquidacionRelacionGrupo)
    assert grupo.codigo.startswith("LQG-")
    assert isinstance(miembro, LiquidacionRelacionMiembro)
    assert miembro.liquidacion == lg
    assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)
    assert miembro.numero_revision == 1


@pytest.mark.django_db
def test_po_base_crear_relacion_grupo_nueva_revision_adds_to_existing_group(
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: liquidacion_previa has an existing group with relacion_key EDIFICACION-OBRA
    WHEN: _crear_relacion_grupo_nueva_revision is called for a new liquidacion
    THEN: the new liquidacion is added to the same group with next revision number
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_po.liquidacion_po_base_flujo import (
        LiquidacionPOBaseFlujo,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
        LiquidacionPorcentajeObraCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcretePOBase(LiquidacionPOBaseFlujo):
        def _get_tipo_liquidacion_code(self):
            return "EDIFICACION"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _calcular_cotizacion(self, **kwargs):
            pass

    flujo = ConcretePOBase(
        porcentaje_core=LiquidacionPorcentajeObraCoreService(),
        general_core=LiquidacionGeneralCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg_previa = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_nueva = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Previa creates group
    grupo, _ = flujo._crear_relacion_grupo_primera_revision(
        liquidacion_general=lg_previa,
        tipo_tramite="OBRA_NUEVA",
    )

    # Nueva revision adds to same group
    miembro_nuevo, fue_backfill = flujo._crear_relacion_grupo_nueva_revision(
        liquidacion_previa=lg_previa,
        liquidacion_general=lg_nueva,
        tipo_tramite="OBRA_NUEVA",
    )

    assert fue_backfill is False
    assert miembro_nuevo.grupo == grupo
    assert miembro_nuevo.liquidacion == lg_nueva
    assert miembro_nuevo.numero_revision == 3
    assert miembro_nuevo.relacion_key == generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)

    # Previa member still in same group
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_previa).exists()


# ── LiquidacionM2FlujoBase helper tests ────────────────────────────────────────

@pytest.mark.django_db
def test_m2_base_calcular_siguiente_numero_revision_1_to_3(
    tipo_habilitacion_urbana,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: a liquidacion with numero_revision=1
    WHEN: _calcular_siguiente_numero_revision is called
    THEN: it returns 3
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_m2.liquidacion_m2_base_flujo import (
        LiquidacionM2FlujoBase,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
        LiquidacionPorMetroCuadradoCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcreteM2Base(LiquidacionM2FlujoBase):
        def _get_tipo_liquidacion_code(self):
            return "HABILITACION_URBANA"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _build_result_legacy(self, **kwargs):
            pass

    flujo = ConcreteM2Base(
        general_core=LiquidacionGeneralCoreService(),
        m2_core=LiquidacionPorMetroCuadradoCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    siguiente = flujo._calcular_siguiente_numero_revision(lg)
    assert siguiente == 3


@pytest.mark.django_db
def test_m2_base_crear_relacion_grupo_primera_revision_creates_group_and_member(
    tipo_habilitacion_urbana,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: a saved LiquidacionGeneral with numero_revision=1
    WHEN: _crear_relacion_grupo_primera_revision is called
    THEN: a new group is created with the liquidacion as member
          and relacion_key is HU (no tipo_tramite for M2)
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_m2.liquidacion_m2_base_flujo import (
        LiquidacionM2FlujoBase,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
        LiquidacionPorMetroCuadradoCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcreteM2Base(LiquidacionM2FlujoBase):
        def _get_tipo_liquidacion_code(self):
            return "HABILITACION_URBANA"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _build_result_legacy(self, **kwargs):
            pass

    flujo = ConcreteM2Base(
        general_core=LiquidacionGeneralCoreService(),
        m2_core=LiquidacionPorMetroCuadradoCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    grupo, miembro = flujo._crear_relacion_grupo_primera_revision(liquidacion_general=lg)

    assert isinstance(grupo, LiquidacionRelacionGrupo)
    assert grupo.codigo.startswith("LQG-")
    assert isinstance(miembro, LiquidacionRelacionMiembro)
    assert miembro.liquidacion == lg
    assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.HABILITACION_URBANA)
    assert miembro.numero_revision == 1


@pytest.mark.django_db
def test_m2_base_crear_relacion_grupo_nueva_revision_adds_to_existing_group(
    tipo_habilitacion_urbana,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: liquidacion_previa has an existing group with relacion_key HU
    WHEN: _crear_relacion_grupo_nueva_revision is called for a new liquidacion
    THEN: the new liquidacion is added to the same group with next revision number
    """
    from modules.liquidaciones.domain.services.flujos.liquidacion_m2.liquidacion_m2_base_flujo import (
        LiquidacionM2FlujoBase,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
        LiquidacionRelacionCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
        LiquidacionPorMetroCuadradoCoreService,
    )
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
        LiquidacionGeneralCoreService,
    )

    class ConcreteM2Base(LiquidacionM2FlujoBase):
        def _get_tipo_liquidacion_code(self):
            return "HABILITACION_URBANA"

        def _crear_wrapper(self, liquidacion_general):
            pass

        def _build_result(self, **kwargs):
            pass

        def _build_result_legacy(self, **kwargs):
            pass

    flujo = ConcreteM2Base(
        general_core=LiquidacionGeneralCoreService(),
        m2_core=LiquidacionPorMetroCuadradoCoreService(),
        relacion_core=LiquidacionRelacionCoreService(),
    )

    lg_previa = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_nueva = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Previa creates group
    grupo, _ = flujo._crear_relacion_grupo_primera_revision(liquidacion_general=lg_previa)

    # Nueva revision adds to same group
    miembro_nuevo, fue_backfill = flujo._crear_relacion_grupo_nueva_revision(
        liquidacion_previa=lg_previa,
        liquidacion_general=lg_nueva,
    )

    assert fue_backfill is False
    assert miembro_nuevo.grupo == grupo
    assert miembro_nuevo.liquidacion == lg_nueva
    assert miembro_nuevo.numero_revision == 3
    assert miembro_nuevo.relacion_key == generar_relacion_key(TipoLiquidacion.HABILITACION_URBANA)

    # Previa member still in same group
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_previa).exists()
