"""
Smoke test for the new GET /liquidaciones/tarifas (general) endpoint.
Verifies:
1. Returns 200
2. Items have tipo_liquidacion field
3. Multiple tipos are returned (EDIFICACION + HABILITACION_URBANA)
4. Historical query (with dates) also works
5. Existing per-tipo endpoint still works
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

    # Especialidad for EDIFICACION
    esp = EspecialidadRevision.objects.get_or_create(
        slug="test", defaults={"nombre": "Test"}
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

    return {"edif": base_edif, "hu": base_hu}


@pytest.mark.django_db
def test_tarifas_generales_vigentes_sin_fechas(api_client, datos_tarifas_generales):
    """GET /liquidaciones/tarifas (no dates) returns vigentes tarifas across all tipos."""
    response = api_client.get("/liquidaciones/tarifas")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data.get("success", False) is True, f"Expected success=True: {data}"

    result = data["data"]
    assert "items" in result, "Response should have 'items'"
    assert "total" in result, "Response should have 'total'"

    items = result["items"]
    assert len(items) >= 2, f"Expected at least 2 items (EDIFICACION + HU), got {len(items)}"

    # Every item must have tipo_liquidacion
    tipos = sorted(set(item["tipo_liquidacion"] for item in items))
    print(f"TIPOS ENCONTRADOS: {tipos}")
    assert "EDIFICACION" in tipos, "EDIFICACION should be in results"
    assert "HABILITACION_URBANA" in tipos, "HABILITACION_URBANA should be in results"

    # Each item should have the expected structure
    for item in items:
        assert "tipo_liquidacion" in item
        assert "periodo_inicio" in item
        # At least one of the detail fields should be populated
        has_details = (
            item.get("tarifas_porcentaje") is not None
            or item.get("tarifa_m2") is not None
            or item.get("tarifas_visitas") is not None
        )
        assert has_details, f"Item should have at least one detail field: {item}"


@pytest.mark.django_db
def test_tarifas_generales_con_fechas(api_client, datos_tarifas_generales):
    """GET /liquidaciones/tarifas with date range returns historical tarifas."""
    response = api_client.get(
        "/liquidaciones/tarifas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]
    tipos = sorted(set(item["tipo_liquidacion"] for item in items))

    assert "EDIFICACION" in tipos
    assert "HABILITACION_URBANA" in tipos


@pytest.mark.django_db
def test_tarifas_generales_paginacion(api_client, datos_tarifas_generales):
    """GET /liquidaciones/tarifas with page_size returns correct pagination."""
    response = api_client.get("/liquidaciones/tarifas?page=1&page_size=1")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 1
    assert len(result["items"]) <= 1
    assert result["total"] >= 2


@pytest.mark.django_db
def test_per_tipo_endpoint_follows_general(api_client, datos_tarifas_generales):
    """Existing per-tipo endpoint still works after changes."""
    response = api_client.get(
        "/liquidaciones/edificacion/tarifas/historicas?fecha_desde=2024-01-01&fecha_hasta=2025-12-31"
    )

    assert response.status_code == 200, f"Per-tipo endpoint broken: {response.content}"
    data = response.json()
    items = data["data"]["items"]

    # Should have at least 1 item for EDIFICACION
    assert len(items) >= 1, f"Expected >= 1 EDIFICACION item, got {len(items)}"
    assert items[0]["tipo_liquidacion"] == "EDIFICACION"
