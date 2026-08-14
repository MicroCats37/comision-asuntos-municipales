"""
Integration tests for historical tariff and derecho endpoints.

Tests use Ninja's TestClient for proper async handling.
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from config.api import api
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision as Especialidad, EspecialidadRevision
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints."""
    return TestClient(api)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def especialidad_estructuras(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="A01",
        slug="arquitectura",
        nombre="Arquitectura",
    )


@pytest.fixture
def derecho_porcentaje_vigente_2024(db):
    """Create a DerechoPorcentajeObra for 2024."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


@pytest.fixture
def derecho_porcentaje_vigente_2025(db):
    """Create a DerechoPorcentajeObra for 2025 (current)."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("550.00"),
        derecho_maximo=Decimal("55000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_m2_vigente_2024(db):
    """Create a DerechoPorMetroCuadrado for 2024."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


@pytest.fixture
def derecho_m2_vigente_2025(db):
    """Create a DerechoPorMetroCuadrado for 2025 (current)."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("110.00"),
        derecho_maximo=Decimal("11000.00"),
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )


# ── GET /liquidaciones/{tipo}/tarifas/historicas Tests ────────────────────────


@pytest.mark.django_db
def test_tarifas_historicas_edificaciones(
    api_client,
    tarifa_liquidacion_base_edificacion,
    especialidad_estructuras,
    especialidad_arquitectura,
    tarifa_porcentaje_obra_estructuras,
    tarifa_porcentaje_obra_arquitectura,
):
    """
    GET /liquidaciones/edificacion/tarifas/historicas returns periods with tarifas.
    """
    response = api_client.get(
        f"/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31&page=1&page_size=10"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "items" in result, "Result should have 'items'"
    assert "total" in result, "Result should have 'total'"

    items = result["items"]
    assert len(items) == 1, f"Expected 1 periodo, got {len(items)}"

    periodo = items[0]
    assert periodo["tipo_liquidacion"] == "EDIFICACION"
    assert len(periodo["tarifas_porcentaje"]) == 2, \
        f"Expected 2 tarifas_porcentaje, got {len(periodo['tarifas_porcentaje'])}"


@pytest.mark.django_db
def test_tarifas_historicas_hu(
    api_client,
    tipo_habilitacion_urbana,
):
    """
    GET /liquidaciones/habilitacion-urbana/tarifas/historicas returns M2 tariff detail.
    """
    # Create HU tariff base and M2 detail
    
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("25.00"),
    )

    response = api_client.get(
        f"/liquidaciones/habilitacion-urbana/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31&page=1&page_size=10"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    items = result["items"]

    assert len(items) == 1
    periodo = items[0]
    assert periodo["tarifa_m2"] is not None, "HU should have tarifa_m2"
    assert float(periodo["tarifa_m2"]["costo_por_m2"]) == 25.00


@pytest.mark.django_db
def test_tarifas_historicas_inspeccion_obras(
    api_client,
    tipo_inspeccion_obra,
):
    """
    GET /liquidaciones/inspeccion-obra/tarifas/historicas returns visitas categories.
    Note: Due to OneToOne constraint on TarifaPorCategoriaVisitas, each category needs its own base.
    """
    # Create multiple IO tariff bases, one per category (since OneToOne limits one per base)
    
    for i, (categoria, pct_uit) in enumerate([("A", "0.05"), ("B", "0.08")]):
        base = TarifaLiquidacionBase.objects.create(
            tipo_liquidacion=tipo_inspeccion_obra,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        TarifaPorCategoriaVisitas.objects.create(
            tarifa_base=base,
            porcentaje_uit=Decimal(pct_uit),
            categoria_visitas=categoria,
        )

    response = api_client.get(
        f"/liquidaciones/inspeccion-obra/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31&page=1&page_size=10"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    items = result["items"]

    assert len(items) == 2, f"Expected 2 periods (one per category), got {len(items)}"


@pytest.mark.django_db
def test_tarifas_historicas_empty_result(
    api_client,
    db,
):
    """
    GET returns empty items when no historical records match.
    """
    response = api_client.get(
        f"/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2020-01-01&fecha_hasta=2020-12-31&page=1&page_size=10"
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.django_db
def test_tarifas_historicas_pagination(
    api_client,
    tipo_edificacion,
):
    """
    GET respects page and page_size parameters.
    """
    # Create multiple tariff bases
    
    for i in range(3):
        base = TarifaLiquidacionBase.objects.create(
            tipo_liquidacion=tipo_edificacion,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        TarifaPorcentajeObra.objects.create(
            tarifa_base=base,
            especialidad=EspecialidadRevision.objects.create(codigo=f"E{i}", slug=f"especialidad-{i}", nombre=f"Especialidad {i}"),
            porcentaje_liquidacion=Decimal("0.0010"),
        )

    # Page 1 with page_size 2
    response = api_client.get(
        f"/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31&page=1&page_size=2"
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert len(result["items"]) == 2
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_pages"] == 2


# ── GET /liquidaciones/derechos/historicos Tests ─────────────────────────────


@pytest.mark.django_db
def test_derechos_historicos_porcentaje(
    api_client,
    derecho_porcentaje_vigente_2024,
    derecho_porcentaje_vigente_2025,
):
    """
    GET /liquidaciones/derechos/historicos?tipo=PORCENTAJE returns derechos.
    """
    response = api_client.get(
        f"/liquidaciones/derechos/historicos?tipo=PORCENTAJE&fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "derechos" in result, "Result should have 'derechos'"

    derechos = result["derechos"]
    assert len(derechos) == 2, f"Expected 2 derechos, got {len(derechos)}"


@pytest.mark.django_db
def test_derechos_historicos_m2(
    api_client,
    derecho_m2_vigente_2024,
    derecho_m2_vigente_2025,
):
    """
    GET /liquidaciones/derechos/historicos?tipo=METRO_CUADRADO returns derechos.
    """
    response = api_client.get(
        f"/liquidaciones/derechos/historicos?tipo=METRO_CUADRADO&fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    derechos = result["derechos"]

    assert len(derechos) == 2


@pytest.mark.django_db
def test_derechos_historicos_empty(
    api_client,
    db,
):
    """
    GET returns empty list when no derechos match.
    """
    response = api_client.get(
        f"/liquidaciones/derechos/historicos?tipo=PORCENTAJE&fecha_desde=2020-01-01&fecha_hasta=2020-12-31"
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert result["derechos"] == []


@pytest.mark.django_db
def test_derechos_historicos_fields(
    api_client,
    derecho_porcentaje_vigente_2024,
):
    """
    Derecho records have correct fields in response.
    """
    response = api_client.get(
        f"/liquidaciones/derechos/historicos?tipo=PORCENTAJE&fecha_desde=2024-01-01&fecha_hasta=2024-12-31"
    )

    assert response.status_code == 200

    data = response.json()
    derechos = data["data"]["derechos"]
    assert len(derechos) == 1

    d = derechos[0]
    assert "id" in d
    assert "derecho_minimo" in d
    assert "derecho_maximo" in d
    assert "porcentaje_minimo_uit" in d
    assert "periodo_inicio" in d
    assert "periodo_fin" in d
    assert float(d["derecho_minimo"]) == 500.00


# ── Overlap Bug Reproduction Tests ─────────────────────────────────────────────

@pytest.mark.django_db
def test_tarifas_historicas_overlap_periodo_fin_null(api_client, tipo_edificacion):
    """
    Regression: GET returns tariff whose periodo_inicio is BEFORE fecha_desde
    but periodo_fin is NULL (ongoing) — the periods OVERLAP and MUST be included.

    Bug: The original filter required periodo_inicio >= fecha_desde, which
    wrongly excluded tariffs that started earlier but are still active.
    """
    # Tarifa starts 2024, still ongoing (periodo_fin=None)
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorcentajeObra.objects.create(
        tarifa_base=base,
        especialidad=EspecialidadRevision.objects.create(codigo="OVLP", nombre="Overlap"),
        porcentaje_liquidacion=Decimal("0.0015"),
    )

    # Query from 2025 onwards — the 2024-ongoing tariff OVERLAPS this range
    response = api_client.get(
        f"/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2025-01-01&fecha_hasta=2026-12-31&page=1&page_size=10"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    items = result["items"]

    # The ongoing 2024 tariff IS active during 2025-2026, so it MUST appear
    assert len(items) == 1, f"Expected 1 overlapping tariff (ongoing from 2024), got {len(items)}: {items}"
    assert items[0]["periodo_inicio"] == "2024-01-01"
    assert items[0]["periodo_fin"] is None


@pytest.mark.django_db
def test_derechos_historicos_overlap_periodo_fin_null(api_client, db):
    """
    Regression: GET /liquidaciones/derechos/historicos returns derecho whose
    periodo_inicio is BEFORE fecha_desde but periodo_fin is NULL (ongoing).
    Same overlap bug as tarifas_historicas.
    """
    # Derecho starts 2024, still ongoing
    derecho = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.14"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    # Query from 2025 onwards — the 2024-ongoing derecho OVERLAPS
    response = api_client.get(
        f"/liquidaciones/derechos/historicos?tipo=PORCENTAJE&fecha_desde=2025-01-01&fecha_hasta=2026-12-31"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    derechos = data["data"]["derechos"]

    assert len(derechos) == 1, f"Expected 1 overlapping derecho (ongoing from 2024), got {len(derechos)}: {derechos}"
    assert derechos[0]["periodo_inicio"] == "2024-01-01"
    assert derechos[0]["periodo_fin"] is None
