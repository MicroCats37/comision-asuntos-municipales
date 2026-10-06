"""
Integration tests for LiquidacionPatchHistoricoCoreService — historical tariff resolution.

Tests the shared historical resolution service that PATCH recalculation uses
to resolve IGV, UIT, tarifas, and derechos by their values vigente at
LiquidacionGeneral.fecha_registro.date().

Coverage:
1. IGV/UIT manual filter by fecha (no manager's vigente() fallback)
2. TarifaLiquidacionBase by tipo_liquidacion + fecha
3. DerechoPorcentajeObra by fecha (newest at fecha, not oldest)
4. DerechoPorMetroCuadrado by fecha (newest at fecha, not oldest)
5. No fallback to current values — raises BusinessError
6. Overlapping periods: selects NEWEST at fecha
"""
import pytest
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
    NoIGVVigenteError,
    NoUITVigenteError,
    NoTarifaVigenteError,
    NoDerechoVigenteError,
)
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.tests.fixtures.tipos_fixtures import (
    tipo_edificacion,
    tipo_habilitacion_urbana,
)


@pytest.fixture
def servicio():
    return LiquidacionPatchHistoricoCoreService()


# ── IGV by fecha ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_igv_por_fecha_returns_correct_record(servicio, db):
    """
    Manual filter returns the IGV vigente at the specific fecha,
    not the current one.
    """
    # Old IGV: Jan 2025 - Dec 2025
    old_igv = IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )
    # Current IGV: Jan 2026 - open
    current_igv = IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    # Query for a date in 2025 — should get old_igv
    result = servicio.get_igv_por_fecha(date(2025, 6, 15))
    assert result.id == old_igv.id
    assert result.valor == Decimal("0.18")


@pytest.mark.django_db
def test_get_igv_por_fecha_raises_when_not_found(servicio, db):
    """
    Raises NoIGVVigenteError when no IGV covers the given fecha.
    Does NOT fallback to the current vigente.
    """
    # Create an IGV that ended before the query date
    IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoIGVVigenteError) as exc_info:
        servicio.get_igv_por_fecha(date(2025, 6, 15))

    assert "No existe IGV vigente" in str(exc_info.value.message)
    assert "2025-06-15" in str(exc_info.value.message)


@pytest.mark.django_db
def test_get_igv_por_fecha_selects_correct_for_non_overlapping_periods(servicio, db):
    """
    When two IGV records have non-overlapping periods, selects the one covering the query date.
    Note: IGV DecimalField uses max_digits=3, decimal_places=2 — values like 0.185 are
    rounded to 0.18 on save, so we use non-overlapping periods to distinguish records.
    """
    # Older: Jan-Mar 2026
    older = IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 3, 31),
    )
    # Newer: Apr 2026 - open
    newer = IGV.objects.create(
        valor=Decimal("0.19"),  # Distinct value (0.19 saves correctly as 3-digit Decimal)
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    # Query for May 2026 — only newer covers it
    result = servicio.get_igv_por_fecha(date(2026, 5, 1))
    assert result.id == newer.id
    assert result.valor == Decimal("0.19")

    # Query for Feb 2026 — only older covers it
    result2 = servicio.get_igv_por_fecha(date(2026, 2, 15))
    assert result2.id == older.id
    assert result2.valor == Decimal("0.18")


# ── UIT by fecha ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_uit_por_fecha_returns_correct_record(servicio, db):
    """
    Manual filter returns the UIT vigente at the specific fecha.
    """
    # Old UIT: 2024
    old_uit = UIT.objects.create(
        valor=4700,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )
    # Current UIT: 2025
    current_uit = UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )

    # Query for a date in 2024
    result = servicio.get_uit_por_fecha(date(2024, 6, 15))
    assert result.id == old_uit.id
    assert result.valor == 4700


@pytest.mark.django_db
def test_get_uit_por_fecha_raises_when_not_found(servicio, db):
    """
    Raises NoUITVigenteError when no UIT covers the given fecha.
    Does NOT fallback to current.
    """
    UIT.objects.create(
        valor=4700,
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoUITVigenteError) as exc_info:
        servicio.get_uit_por_fecha(date(2025, 6, 15))

    assert "No existe UIT vigente" in str(exc_info.value.message)


@pytest.mark.django_db
def test_get_uit_por_fecha_overlapping_selects_newest(servicio, db):
    """
    When two UIT records overlap at fecha, selects the NEWEST by periodo_inicio.
    """
    older = UIT.objects.create(
        valor=4700,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer = UIT.objects.create(
        valor=4800,
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    result = servicio.get_uit_por_fecha(date(2026, 5, 1))
    assert result.id == newer.id
    assert result.valor == 4800


# ── TarifaLiquidacionBase by tipo_liquidacion + fecha ─────────────────────────


@pytest.mark.django_db
def test_get_tarifa_base_vigente_returns_base(servicio, db, tipo_edificacion):
    """
    Returns the TarifaLiquidacionBase vigente at fecha for the given tipo.
    """
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_tarifa_base_vigente("EDIFICACION", date(2026, 6, 1))
    assert result.id == base.id


@pytest.mark.django_db
def test_get_tarifa_base_vigente_raises_when_not_found(servicio, db, tipo_edificacion):
    """
    Raises NoTarifaVigenteError when no base tariff is vigente at fecha.
    Does NOT fallback to current.
    """
    # Create a tariff that ended before the query date
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoTarifaVigenteError) as exc_info:
        servicio.get_tarifa_base_vigente("EDIFICACION", date(2025, 6, 15))

    assert "No existe tarifa base vigente para EDIFICACION" in str(exc_info.value.message)
    assert "2025-06-15" in str(exc_info.value.message)


@pytest.mark.django_db
def test_get_tarifa_base_vigente_overlapping_selects_newest(servicio, db, tipo_edificacion):
    """
    When two TarifaLiquidacionBase records overlap at fecha,
    selects the NEWEST by periodo_inicio.
    """
    older = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    result = servicio.get_tarifa_base_vigente("EDIFICACION", date(2026, 5, 1))
    assert result.id == newer.id


@pytest.mark.django_db
def test_get_tarifa_base_vigente_respects_tipo_liquidacion(servicio, db, tipo_edificacion, tipo_habilitacion_urbana):
    """
    Query for EDIFICACION does NOT return a HABILITACION_URBANA tariff.
    """
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

    result = servicio.get_tarifa_base_vigente("EDIFICACION", date(2026, 6, 1))
    assert result.id == edificacion_base.id


@pytest.mark.django_db
def test_get_tarifa_base_vigente_list_returns_all_overlapping(servicio, db, tipo_edificacion):
    """
    get_tarifa_base_vigente_list returns ALL overlapping records (newest first).
    """
    older = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    result = servicio.get_tarifa_base_vigente_list("EDIFICACION", date(2026, 5, 1))
    assert len(result) == 2
    # Newest first
    assert result[0].id == newer.id
    assert result[1].id == older.id


# ── TarifaPorcentajeObra ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_tarifa_porcentaje_obra_returns_records(servicio, db, tipo_edificacion):
    """
    Returns TarifaPorcentajeObra records for the given base IDs.
    """
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    po = TarifaPorcentajeObra.objects.create(
        tarifa_base=base,
        porcentaje_liquidacion=Decimal("0.0015"),
    )

    result = servicio.get_tarifa_porcentaje_obra([str(base.id)])
    assert len(result) == 1
    assert result[0].id == po.id


@pytest.mark.django_db
def test_get_tarifa_porcentaje_obra_empty_for_empty_ids(servicio, db):
    """
    Returns empty list when given empty IDs list.
    """
    result = servicio.get_tarifa_porcentaje_obra([])
    assert result == []


# ── TarifaPorMetroCuadrado ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_tarifa_m2_returns_record(servicio, db, tipo_habilitacion_urbana):
    """
    Returns TarifaPorMetroCuadrado for the given base ID.
    """
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    m2 = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("25.0000"),
    )

    result = servicio.get_tarifa_m2(str(base.id))
    assert result is not None
    assert result.id == m2.id


@pytest.mark.django_db
def test_get_tarifa_m2_returns_none_when_not_found(servicio, db):
    """
    Returns None when no TarifaPorMetroCuadrado exists for the base ID.
    """
    result = servicio.get_tarifa_m2("00000000-0000-0000-0000-000000000000")
    assert result is None


# ── TarifaPorCategoriaVisitas ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_tarifa_categoria_visitas_returns_records(servicio, db, tipo_edificacion):
    """
    Returns TarifaPorCategoriaVisitas records for the given base IDs.
    """
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    vis = TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base,
        categoria_visitas="INSPECCION",
        porcentaje_uit=Decimal("0.05"),
    )

    result = servicio.get_tarifa_categoria_visitas([str(base.id)])
    assert len(result) == 1
    assert result[0].id == vis.id


@pytest.mark.django_db
def test_get_tarifa_categoria_visitas_empty_for_empty_ids(servicio, db):
    """
    Returns empty list when given empty IDs list.
    """
    result = servicio.get_tarifa_categoria_visitas([])
    assert result == []


# ── DerechoPorcentajeObra by fecha ─────────────────────────────────────────────


@pytest.mark.django_db
def test_get_derecho_porcentaje_vigente_returns_record(servicio, db):
    """
    Returns the DerechoPorcentajeObra vigente at fecha.
    """
    derecho = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_derecho_porcentaje_vigente(date(2026, 6, 1))
    assert result.id == derecho.id


@pytest.mark.django_db
def test_get_derecho_porcentaje_vigente_raises_when_not_found(servicio, db):
    """
    Raises NoDerechoVigenteError when no derecho is vigente at fecha.
    Does NOT fallback to current.
    """
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoDerechoVigenteError) as exc_info:
        servicio.get_derecho_porcentaje_vigente(date(2025, 6, 15))

    assert "No existe derecho" in str(exc_info.value.message)
    assert "porcentaje obra" in str(exc_info.value.message)


@pytest.mark.django_db
def test_get_derecho_porcentaje_vigente_overlapping_selects_newest(servicio, db):
    """
    When two DerechoPorcentajeObra records overlap at fecha,
    selects the NEWEST by periodo_inicio.
    Prior exploration found ASC ordering was a bug here — this test verifies DESC.
    """
    older = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    result = servicio.get_derecho_porcentaje_vigente(date(2026, 5, 1))
    # NEWEST by periodo_inicio = newer
    assert result.id == newer.id
    assert result.derecho_minimo == Decimal("600.00")


# ── DerechoPorMetroCuadrado by fecha ──────────────────────────────────────────


@pytest.mark.django_db
def test_get_derecho_m2_vigente_returns_record(servicio, db):
    """
    Returns the DerechoPorMetroCuadrado vigente at fecha.
    """
    derecho = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_derecho_m2_vigente(date(2026, 6, 1))
    assert result.id == derecho.id


@pytest.mark.django_db
def test_get_derecho_m2_vigente_raises_when_not_found(servicio, db):
    """
    Raises NoDerechoVigenteError when no derecho m2 is vigente at fecha.
    Does NOT fallback to current.
    """
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    with pytest.raises(NoDerechoVigenteError) as exc_info:
        servicio.get_derecho_m2_vigente(date(2025, 6, 15))

    assert "No existe derecho" in str(exc_info.value.message)
    assert "por metro cuadrado" in str(exc_info.value.message)


@pytest.mark.django_db
def test_get_derecho_m2_vigente_overlapping_selects_newest(servicio, db):
    """
    When two DerechoPorMetroCuadrado records overlap at fecha,
    selects the NEWEST by periodo_inicio.
    """
    older = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    newer = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("120.00"),
        derecho_maximo=Decimal("12000.00"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    result = servicio.get_derecho_m2_vigente(date(2026, 5, 1))
    # NEWEST by periodo_inicio = newer
    assert result.id == newer.id
    assert result.derecho_minimo == Decimal("120.00")
