"""
Integration tests for the canonical historical resolver — LiquidacionHistoricoCoreService.

Focused coverage for Phase 1 of `registro-liquidaciones-legacy`:

1. Single canonical owner — the PATCH compatibility export IS the canonical class.
2. Canonical resolution by effective date (IGV, UIT, base tariff, child tariffs, derechos).
3. Domain errors when no historical value covers the date (no silent fallback to today).
4. Legacy PO / M2 / visit adapters delegate historical reads to the canonical
   resolver while preserving their nullable importer-facing contracts.

NOT EXECUTED in Phase 1 — verification is reserved for Phase 5.
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
    TarifaPorCategoriaVisitas,
    TarifaPorMetroCuadrado,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
    NoDerechoVigenteError,
    NoIGVVigenteError,
    NoTarifaVigenteError,
    NoUITVigenteError,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_m2_core_service import (
    LiquidacionLegacyPorM2CoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_porcentaje_core_service import (
    LiquidacionLegacyPorPorcentajeCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from modules.liquidaciones.tests.fixtures.tipos_fixtures import (
    tipo_edificacion,
    tipo_habilitacion_urbana,
)


@pytest.fixture
def resolver():
    """Canonical historical resolver."""
    return LiquidacionHistoricoCoreService()


@pytest.fixture
def legacy_po_core():
    """Legacy PO adapter (porcentaje de obra)."""
    return LiquidacionLegacyPorPorcentajeCoreService(
        tarifas_service=TarifasHistoricasCoreService()
    )


@pytest.fixture
def legacy_m2_core():
    """Legacy M2 adapter (metro cuadrado)."""
    return LiquidacionLegacyPorM2CoreService(
        tarifas_service=TarifasHistoricasCoreService()
    )


@pytest.fixture
def legacy_visitas_core():
    """Legacy visitas adapter (categoría de visitas)."""
    return LiquidacionLegacyPorVisitasCoreService(
        tarifas_service=TarifasHistoricasCoreService()
    )


# ── Canonical ownership ────────────────────────────────────────────────────────


def test_compat_export_is_the_canonical_resolver():
    """
    The PATCH compatibility export is an alias of the canonical resolver:
    one implementation, no duplicated resolution logic.
    """
    assert LiquidacionPatchHistoricoCoreService is LiquidacionHistoricoCoreService


def test_compat_export_keeps_legacy_error_types():
    """The compatibility module still exposes the domain errors it always did."""
    from modules.liquidaciones.domain.services.core import (
        liquidacion_patch_historico_core_service as compat,
    )

    assert compat.NoIGVVigenteError is NoIGVVigenteError
    assert compat.NoUITVigenteError is NoUITVigenteError
    assert compat.NoTarifaVigenteError is NoTarifaVigenteError
    assert compat.NoDerechoVigenteError is NoDerechoVigenteError


# ── Canonical resolution by effective date ─────────────────────────────────────


@pytest.mark.django_db
def test_resolver_igv_por_fecha_usa_el_valor_vigente_en_la_fecha(resolver, db):
    """
    GIVEN two IGV periods covering different dates
    WHEN the resolver is asked for a date inside the older period
    THEN it returns the older record (not the current one).
    """
    old_igv = IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )
    IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = resolver.get_igv_por_fecha(date(2025, 6, 15))

    assert result.id == old_igv.id
    assert result.valor == Decimal("0.18")


@pytest.mark.django_db
def test_resolver_uit_por_fecha_usa_el_valor_vigente_en_la_fecha(resolver, db):
    """
    GIVEN two UIT periods
    WHEN the resolver is asked for a date inside the older period
    THEN it returns the older record.
    """
    old_uit = UIT.objects.create(
        valor=4700,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )
    UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )

    result = resolver.get_uit_por_fecha(date(2024, 6, 15))

    assert result.id == old_uit.id
    assert result.valor == 4700


@pytest.mark.django_db
def test_resolver_tarifa_base_por_fecha_ignora_tarifas_de_otro_tipo(
    resolver, db, tipo_edificacion, tipo_habilitacion_urbana
):
    """
    GIVEN base tariffs for two different tipos
    WHEN the resolver resolves EDIFICACION at a date
    THEN it only returns the EDIFICACION base tariff.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    edificacion_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = resolver.get_tarifa_base_vigente("EDIFICACION", date(2026, 6, 1))

    assert result.id == edificacion_base.id


@pytest.mark.django_db
def test_resolver_tarifas_hijas_por_fecha(resolver, db, tipo_edificacion):
    """
    GIVEN a base tariff vigente at the date with its PO/M2/visitas children
    WHEN the resolver is asked for the child tariffs
    THEN it returns the children of that base.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    porcentaje = TarifaPorcentajeObra.objects.create(
        tarifa_base=base,
        porcentaje_liquidacion=Decimal("0.0015"),
    )
    visitas = TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base,
        categoria_visitas="INSPECCION",
        porcentaje_uit=Decimal("0.05"),
    )

    assert [t.id for t in resolver.get_tarifa_porcentaje_obra([str(base.id)])] == [
        porcentaje.id
    ]
    assert [t.id for t in resolver.get_tarifa_categoria_visitas([str(base.id)])] == [
        visitas.id
    ]
    assert resolver.get_tarifa_porcentaje_obra([]) == []
    assert resolver.get_tarifa_categoria_visitas([]) == []


@pytest.mark.django_db
def test_resolver_tarifa_m2_por_base(resolver, db, tipo_habilitacion_urbana):
    """
    GIVEN a base tariff with its M2 child
    WHEN the resolver is asked for the M2 tariff
    THEN it returns the child, and None when the child does not exist.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    m2 = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("25.0000"),
    )

    result = resolver.get_tarifa_m2(str(base.id))

    assert result is not None
    assert result.id == m2.id
    assert resolver.get_tarifa_m2("00000000-0000-0000-0000-000000000000") is None


@pytest.mark.django_db
def test_resolver_derechos_por_fecha(resolver, db):
    """
    GIVEN percentage and M2 derechos with overlapping periods
    WHEN the resolver resolves them at a date
    THEN it returns the NEWEST record effective at that date.
    """
    older_porcentaje = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer_porcentaje = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    nuevo_m2 = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("120.00"),
        derecho_maximo=Decimal("12000.00"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    porcentaje = resolver.get_derecho_porcentaje_vigente(date(2026, 5, 1))
    m2 = resolver.get_derecho_m2_vigente(date(2026, 5, 1))

    assert porcentaje.id == newer_porcentaje.id
    assert m2.id == nuevo_m2.id
    assert older_porcentaje.id != porcentaje.id


# ── Domain errors — no silent fallback ────────────────────────────────────────


@pytest.mark.django_db
def test_resolver_no_hace_fallback_al_valor_actual_sin_igv(resolver, db):
    """
    GIVEN only a current IGV
    WHEN the resolver is asked for a date it does not cover
    THEN it raises NoIGVVigenteError instead of using today's value.
    """
    IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    with pytest.raises(NoIGVVigenteError) as exc_info:
        resolver.get_igv_por_fecha(date(2025, 6, 15))

    assert "No existe IGV vigente" in str(exc_info.value.message)
    assert "2025-06-15" in str(exc_info.value.message)


@pytest.mark.django_db
def test_resolver_no_hace_fallback_al_valor_actual_sin_uit(resolver, db):
    """
    GIVEN only a current UIT
    WHEN the resolver is asked for a date it does not cover
    THEN it raises NoUITVigenteError instead of using today's value.
    """
    UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )

    with pytest.raises(NoUITVigenteError) as exc_info:
        resolver.get_uit_por_fecha(date(2024, 6, 15))

    assert "No existe UIT vigente" in str(exc_info.value.message)


@pytest.mark.django_db
def test_resolver_no_hace_fallback_al_valor_actual_sin_tarifa_base(
    resolver, db, tipo_edificacion
):
    """
    GIVEN a base tariff that already expired
    WHEN the resolver is asked for a later date
    THEN it raises NoTarifaVigenteError.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoTarifaVigenteError) as exc_info:
        resolver.get_tarifa_base_vigente("EDIFICACION", date(2025, 6, 15))

    assert "No existe tarifa base vigente para EDIFICACION" in str(
        exc_info.value.message
    )


@pytest.mark.django_db
def test_resolver_no_hace_fallback_al_valor_actual_sin_derecho(resolver, db):
    """
    GIVEN derechos that already expired
    WHEN the resolver is asked for a later date
    THEN it raises NoDerechoVigenteError.
    """
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoDerechoVigenteError) as exc_info:
        resolver.get_derecho_porcentaje_vigente(date(2025, 6, 15))

    assert "No existe derecho" in str(exc_info.value.message)
    assert "porcentaje obra" in str(exc_info.value.message)


# ── Legacy PO adapter ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_legacy_porcentaje_delega_al_resolver_canonico(
    legacy_po_core, db, tipo_edificacion
):
    """
    GIVEN a base tariff and a derecho vigente at the date
    WHEN the legacy PO adapter is asked for them
    THEN it returns the same records the canonical resolver returns.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    porcentaje = TarifaPorcentajeObra.objects.create(
        tarifa_base=base,
        porcentaje_liquidacion=Decimal("0.0015"),
    )
    derecho = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    tarifas = legacy_po_core.get_tarifa_por_fecha("EDIFICACION", date(2026, 6, 1))
    resuelto_derecho = legacy_po_core.get_derecho_porcentaje_por_fecha(
        date(2026, 6, 1)
    )

    assert [t.id for t in tarifas] == [porcentaje.id]
    assert resuelto_derecho.id == derecho.id
    assert [
        d.id for d in legacy_po_core.get_derechos_porcentaje_list(date(2026, 6, 1))
    ] == [derecho.id]


@pytest.mark.django_db
def test_legacy_porcentaje_preserva_contrato_nullable(legacy_po_core, db):
    """
    GIVEN no historical tariff nor derecho for the date
    WHEN the legacy PO adapter is asked for them
    THEN it returns an empty list and None — it never raises.
    """
    assert legacy_po_core.get_tarifa_por_fecha("EDIFICACION", date(2025, 6, 1)) == []
    assert legacy_po_core.get_derecho_porcentaje_por_fecha(date(2025, 6, 1)) is None
    assert legacy_po_core.get_derechos_porcentaje_list(date(2025, 6, 1)) == []


# ── Legacy M2 adapter ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_legacy_m2_delega_al_resolver_canonico(
    legacy_m2_core, db, tipo_habilitacion_urbana
):
    """
    GIVEN a base tariff with its M2 child and a derecho vigente at the date
    WHEN the legacy M2 adapter is asked for them
    THEN it returns the same records the canonical resolver returns.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    m2 = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("25.0000"),
    )
    derecho = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    assert legacy_m2_core.get_tarifa_m2_por_fecha(
        "HABILITACION_URBANA", date(2026, 6, 1)
    ).id == m2.id
    assert legacy_m2_core.get_derecho_m2_por_fecha(date(2026, 6, 1)).id == derecho.id
    assert [
        d.id for d in legacy_m2_core.get_derechos_m2_list(date(2026, 6, 1))
    ] == [derecho.id]
    assert [
        b.id for b in legacy_m2_core.get_tarifas_base_list("HABILITACION_URBANA", date(2026, 6, 1))
    ] == [base.id]


@pytest.mark.django_db
def test_legacy_m2_preserva_contrato_nullable(legacy_m2_core, db):
    """
    GIVEN no historical M2 tariff nor derecho for the date
    WHEN the legacy M2 adapter is asked for them
    THEN it returns None — it never raises.
    """
    assert legacy_m2_core.get_tarifa_m2_por_fecha("MECANICA_SUELOS", date(2025, 6, 1)) is None
    assert legacy_m2_core.get_derecho_m2_por_fecha(date(2025, 6, 1)) is None
    assert legacy_m2_core.get_derechos_m2_list(date(2025, 6, 1)) == []
    assert legacy_m2_core.get_tarifas_base_list("MECANICA_SUELOS", date(2025, 6, 1)) == []


def test_legacy_m2_conserva_el_constructor_de_los_importadores():
    """
    The legacy import commands build the M2 adapter with the `tarifas_service`
    keyword — that importer-facing contract must keep working.
    """
    core = LiquidacionLegacyPorM2CoreService(
        tarifas_service=TarifasHistoricasCoreService()
    )

    assert isinstance(core, LiquidacionLegacyPorM2CoreService)


# ── Legacy visitas adapter ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_legacy_visitas_delega_al_resolver_canonico(
    legacy_visitas_core, db, tipo_edificacion
):
    """
    GIVEN a base tariff with its visitas child plus IGV/UIT covering the date
    WHEN the legacy visitas adapter is asked for them
    THEN it returns the same records the canonical resolver returns.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    visitas = TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base,
        categoria_visitas="INSPECCION",
        porcentaje_uit=Decimal("0.05"),
    )
    igv = IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    uit = UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    tarifas = legacy_visitas_core.get_tarifa_visitas_por_fecha(
        "EDIFICACION", date(2026, 6, 1)
    )

    assert [t.id for t in tarifas] == [visitas.id]
    assert legacy_visitas_core.get_igv_por_fecha(date(2026, 6, 1)).id == igv.id
    assert legacy_visitas_core.get_uit_por_fecha(date(2026, 6, 1)).id == uit.id
    assert [
        b.id
        for b in legacy_visitas_core.get_tarifas_base_list("EDIFICACION", date(2026, 6, 1))
    ] == [base.id]


@pytest.mark.django_db
def test_legacy_visitas_preserva_contrato_nullable(legacy_visitas_core, db):
    """
    GIVEN no historical IGV/UIT/tarifa for the date
    WHEN the legacy visitas adapter is asked for them
    THEN it returns None / empty list — the canonical domain errors are
    translated back into the nullable importer contract.
    """
    assert legacy_visitas_core.get_igv_por_fecha(date(2025, 6, 1)) is None
    assert legacy_visitas_core.get_uit_por_fecha(date(2025, 6, 1)) is None
    assert (
        legacy_visitas_core.get_tarifa_visitas_por_fecha("EDIFICACION", date(2025, 6, 1))
        == []
    )
    assert legacy_visitas_core.get_tarifas_base_list("EDIFICACION", date(2025, 6, 1)) == []
