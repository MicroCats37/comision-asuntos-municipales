"""
Integration tests for Mecánica de Suelos GET / list endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET / returns 200 with PaginatedData structure
- Pagination params (page, page_size)
- Response contains LiquidacionMecanicaSuelosOutput items
- Empty list returns empty items array

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_ms(db, tipo_mecanica_suelos):
    """Create a TarifaLiquidacionBase for Mecánica de Suelos."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_liquidacion_base_ms):
    """Create a TarifaPorMetroCuadrado for Mecánica de Suelos."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_ms,
        costo_por_m2=Decimal("150.00"),
    )


@pytest.fixture
def derecho_m2_ms(db):
    """Create a DerechoPorMetroCuadrado vigente for testing."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_ms_created(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_m2_ms,
    igv_vigente,
    uit_vigente,
    tarifa_m2_ms,
    tipo_mecanica_suelos,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionMecanicaSuelos + LiquidacionPorMetroCuadrado
    for testing the list endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-MS-2024-001",
        observacion="Test liquidation MS",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("15000.00"),
        total=Decimal("17700.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionMecanicaSuelos (identity)
    ms = LiquidacionMecanicaSuelos.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorMetroCuadrado
    m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("100.00"),
        costo_por_m2=tarifa_m2_ms.costo_por_m2,
        derecho_minimo=derecho_m2_ms.derecho_minimo,
        derecho_maximo=derecho_m2_ms.derecho_maximo,
        tarifa_aplicada=tarifa_m2_ms,
        derecho=derecho_m2_ms,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_endpoint_returns_200(
    auth_client,
    liquidacion_ms_created,
):
    """
    GET /liquidaciones/mecanica-suelos/ returns 200.
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_response_has_paginated_data_structure(
    auth_client,
    liquidacion_ms_created,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "items" in result, "PaginatedData should have 'items'"
    assert "total" in result, "PaginatedData should have 'total'"
    assert "page" in result, "PaginatedData should have 'page'"
    assert "page_size" in result, "PaginatedData should have 'page_size'"
    assert "total_pages" in result, "PaginatedData should have 'total_pages'"


@pytest.mark.django_db
def test_list_response_contains_liquidacion_ms_output(
    auth_client,
    liquidacion_ms_created,
):
    """
    Each item in items has the LiquidacionMecanicaSuelosOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["items"]) >= 1, "Should have at least 1 item"

    item = result["items"][0]
    assert "liquidacion_general" in item, \
        "Item should have 'liquidacion_general'"
    assert "liquidacion_especifica" in item, \
        "Item should have 'liquidacion_especifica'"
    assert "liquidacion_tipo" in item, \
        "Item should have 'liquidacion_tipo'"


@pytest.mark.django_db
def test_list_pagination_params_work(auth_client, liquidacion_ms_created):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/?page=1&page_size=5")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 5


@pytest.mark.django_db
def test_list_empty_returns_empty_items(auth_client, db):
    """
    When no liquidaciones exist, returns empty items array with total=0.
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


@pytest.mark.django_db
def test_list_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_ms_created,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lg = item["liquidacion_general"]

    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert "fecha_registro" in lg
    assert "expediente" in lg
    assert "numero_revision" in lg
    assert "sub_total" in lg
    assert "total" in lg
    assert "proyecto" in lg


@pytest.mark.django_db
def test_list_liquidacion_especifica_has_identity_fields(
    auth_client,
    liquidacion_ms_created,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    le = item["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "area_m2" not in le, \
        "liquidacion_especifica should NOT have area_m2"


@pytest.mark.django_db
def test_list_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_ms_created,
):
    """
    liquidacion_tipo wrapper has calculation fields: area_m2, costo_por_m2, etc.
    """
    response = auth_client.get("/liquidaciones/mecanica-suelos/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert "id" in lt
    assert "area_m2" in lt
    assert "costo_por_m2" in lt
    assert "derecho_minimo" in lt
    assert "tarifa_aplicada_id" in lt
    assert "derecho_aplicado_id" in lt