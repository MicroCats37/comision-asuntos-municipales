"""
Tests for GET /liquidaciones/tarifas (general) endpoint.
Verifies:
1. Returns 200 with unpaginated array data
2. Items have tipo_tarifa discriminator and only their typed detail key
3. No irrelevant empty arrays in items
4. vigentes=true returns only vigentes (default)
5. vigentes=false with date range returns historical
6. Per-tipo endpoint still works
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from config.api import api
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorcentajeObra,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


@pytest.fixture
def api_client(db):
    return TestClient(api)


@pytest.fixture
def datos_tarifas_generales(db):
    """Create test data across multiple tipos: EDIFICACION (PO) + HABILITACION_URBANA (M2)."""
    # Get tipos
    tipo_edif = TipoLiquidacion.objects.get_or_create(
        codigo="EDIFICACION", defaults={"nombre": "Edificaciones"}
    )[0]
    tipo_hu = TipoLiquidacion.objects.get_or_create(
        codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"}
    )[0]
    tipo_io = TipoLiquidacion.objects.get_or_create(
        codigo="INSPECCION_OBRA", defaults={"nombre": "Inspección de Obra"}
    )[0]

    # Especialidad for EDIFICACION
    esp = EspecialidadRevision.objects.get_or_create(
        slug="test", defaults={"nombre": "Test"}
    )[0]
    esp_2 = EspecialidadRevision.objects.get_or_create(
        slug="test-2", defaults={"nombre": "Test 2"}
    )[0]

    # Base EDIFICACION (PorcentajeObra)
    base_edif = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edif,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorcentajeObra.objects.create(
        tarifa_base=base_edif,
        porcentaje_liquidacion=Decimal("0.0010"),
    )
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_edif,
        especialidad=esp,
        activo=True,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_edif,
        especialidad=esp_2,
        activo=True,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    # Base HABILITACION_URBANA (M2)
    base_hu = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_hu,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base_hu,
        costo_por_m2=Decimal("25.0000"),
    )

    # Base INSPECCION_OBRA (Visitas) with two categories
    base_io = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_io,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base_io,
        categoria_visitas="A",
        porcentaje_uit=Decimal("0.0500"),
    )
    TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base_io,
        categoria_visitas="B",
        porcentaje_uit=Decimal("0.0600"),
    )

    # Non-vigente historical base: must appear when no vigentes filter is active.
    base_edif_historica = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edif,
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )
    TarifaPorcentajeObra.objects.create(
        tarifa_base=base_edif_historica,
        porcentaje_liquidacion=Decimal("0.0005"),
    )

    return {"edif": base_edif, "hu": base_hu, "io": base_io, "edif_historica": base_edif_historica}


@pytest.mark.django_db
def test_tarifas_generales_default_returns_all_registered(api_client, datos_tarifas_generales):
    """
    GET /liquidaciones/tarifas returns all registered tariffs by default.
    No page/page_size in response. Each item has tipo_tarifa discriminator.
    """
    response = api_client.get("/liquidaciones/tarifas")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data.get("success", False) is True, f"Expected success=True: {data}"

    # Response is an array directly (no PaginatedData wrapper)
    items = data["data"]
    assert isinstance(items, list), f"Expected array, got {type(items)}: {items}"

    assert len(items) >= 7, f"Expected expanded items including non-vigente historical tariff, got {len(items)}"
    assert any(item["periodo_fin"] == "2020-12-31" for item in items), (
        "Default endpoint must include non-vigente historical tariffs when no vigentes filter is active"
    )

    # Every item must have tipo_tarifa discriminator
    tipos_encontrados = set()
    for item in items:
        assert "tipo_tarifa" in item, f"Item missing tipo_tarifa: {item}"
        assert "tipo_liquidacion" in item
        assert "periodo_inicio" in item
        tipos_encontrados.add(item["tipo_tarifa"])

        # Check discriminated shape
        if item["tipo_tarifa"] == "porcentaje":
            assert "tarifa_porcentaje" in item
            assert "tarifa_m2" not in item
            assert "tarifa_visitas" not in item
            tarifa = item["tarifa_porcentaje"]
            assert "id" in tarifa
            assert "especialidad" in tarifa
            assert "porcentaje" in tarifa
        elif item["tipo_tarifa"] == "m2":
            assert "tarifa_m2" in item
            assert "tarifa_porcentaje" not in item
            assert "tarifa_visitas" not in item
            tarifa = item["tarifa_m2"]
            assert "id" in tarifa
            assert "monto" in tarifa
        elif item["tipo_tarifa"] == "visitas":
            assert "tarifa_visitas" in item
            assert "tarifa_porcentaje" not in item
            assert "tarifa_m2" not in item

    assert "porcentaje" in tipos_encontrados, "Should have porcentaje items"
    assert "m2" in tipos_encontrados, "Should have m2 items"
    assert "visitas" in tipos_encontrados, "Should have visitas items"

    porcentaje_items = [item for item in items if item["tipo_tarifa"] == "porcentaje"]
    visitas_items = [item for item in items if item["tipo_tarifa"] == "visitas"]
    assert len(porcentaje_items) >= 2, "Should expand each porcentaje detail into its own item"
    assert len(visitas_items) >= 2, "Should expand each visitas category into its own item"


@pytest.mark.django_db
def test_tarifas_generales_vigentes_explicit(api_client, datos_tarifas_generales):
    """GET /liquidaciones/tarifas?vigentes=true returns only vigentes tarifas."""
    response = api_client.get("/liquidaciones/tarifas?vigentes=true")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]

    assert isinstance(items, list)
    assert len(items) >= 2

    # All should be vigentes (periodo_fin is null for our test data)
    for item in items:
        assert item["periodo_fin"] is None, f"Non-vigente item found: {item}"


@pytest.mark.django_db
def test_tarifas_generales_historical_con_fechas(api_client, datos_tarifas_generales):
    """GET /liquidaciones/tarifas?vigentes=false&fecha_desde=X&fecha_hasta=Y returns historical range."""
    response = api_client.get(
        "/liquidaciones/tarifas?vigentes=false&fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]

    assert isinstance(items, list)
    assert len(items) >= 2

    # Items should have tipo_tarifa
    tipos = set(item["tipo_tarifa"] for item in items)
    assert "porcentaje" in tipos
    assert "m2" in tipos


@pytest.mark.django_db
def test_tarifas_generales_no_pagination_metadata(api_client, datos_tarifas_generales):
    """Response has no pagination metadata (no page, page_size, total_pages)."""
    response = api_client.get("/liquidaciones/tarifas")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]

    assert isinstance(items, list)
    # Response should not have pagination fields
    assert "page" not in data["data"], "Should not have page field"
    assert "page_size" not in data["data"], "Should not have page_size field"
    assert "total_pages" not in data["data"], "Should not have total_pages field"


@pytest.mark.django_db
def test_per_tipo_endpoint_still_works(api_client, datos_tarifas_generales):
    """Existing per-tipo endpoint GET /liquidaciones/{tipo}/tarifas/historicas still works."""
    response = api_client.get(
        "/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200, f"Per-tipo endpoint broken: {response.content}"
    data = response.json()
    result = data["data"]

    # Per-tipo endpoint still returns paginated format
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result

    items = result["items"]
    assert len(items) >= 1, f"Expected >= 1 EDIFICACION item, got {len(items)}"
    assert items[0]["tipo_liquidacion"] == "EDIFICACION"
