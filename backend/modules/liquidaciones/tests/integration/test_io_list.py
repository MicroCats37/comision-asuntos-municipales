"""
Integration tests for Inspección de Obra GET / list endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET / returns 200 with PaginatedData structure
- Pagination params (page, page_size)
- Response contains LiquidacionInspeccionObraOutput items
- Empty list returns empty items array

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_io_created(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tipo_inspeccion_obra,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionInspeccionObra + LiquidacionPorCategoriaVisitas
    for testing the list endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-2024-001",
        observacion="Test liquidation IO",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("772.50"),
        total=Decimal("911.55"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionInspeccionObra (identity wrapper)
    io = LiquidacionInspeccionObra.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorCategoriaVisitas (calculation data)
    lv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_endpoint_returns_200(
    auth_client,
    liquidacion_io_created,
):
    """
    GET /liquidaciones/inspeccion-obra/ returns 200.
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_response_has_paginated_data_structure(
    auth_client,
    liquidacion_io_created,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

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
def test_list_response_contains_liquidacion_io_output(
    auth_client,
    liquidacion_io_created,
):
    """
    Each item in items has the LiquidacionInspeccionObraOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

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
def test_list_pagination_params_work(auth_client, liquidacion_io_created):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/?page=1&page_size=5")

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
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


@pytest.mark.django_db
def test_list_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_io_created,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

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
    liquidacion_io_created,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    le = item["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "cantidad_visitas" not in le, \
        "liquidacion_especifica should NOT have cantidad_visitas"


@pytest.mark.django_db
def test_list_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_io_created,
):
    """
    liquidacion_tipo wrapper has calculation fields: cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id.
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert "id" in lt
    assert "cantidad_visitas" in lt
    assert "porcentaje_uit" in lt
    assert "categoria" in lt
    assert "tarifa_aplicada_id" in lt


@pytest.mark.django_db
def test_list_liquidacion_tipo_has_registros_pago_field(
    auth_client,
    liquidacion_io_created,
):
    """
    liquidacion_tipo wrapper includes persisted RegistroPagoInspector rows.
    """
    liquidacion_visitas = liquidacion_io_created.liquidacion_visitas.first()
    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=9,
        inspecciones_pagadas=2,
        fecha_registro=date(2026, 9, 25),
    )

    response = auth_client.get("/liquidaciones/inspeccion-obra/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert "registros_pago" in lt
    assert isinstance(lt["registros_pago"], list)
    assert lt["registros_pago"] == [
        {
            "id": str(liquidacion_visitas.registros_pago.first().id),
            "periodo": 2026,
            "mes": 9,
            "inspecciones_pagadas": 2,
            "fecha_registro": "2026-09-25",
        }
    ]
