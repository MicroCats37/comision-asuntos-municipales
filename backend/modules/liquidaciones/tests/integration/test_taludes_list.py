"""
Integration tests for Taludes GET / list endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET / returns 200 with PaginatedData structure
- Pagination params (page, page_size)
- Response contains LiquidacionTaludesOutput items
- Empty list returns empty items array

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Taludes-specific Tarifa Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_taludes(db, tipo_taludes):
    """Create a TarifaLiquidacionBase for Taludes."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_taludes(db):
    """Create an Especialidad for Taludes testing."""
    from modules.usuarios.domain.models.perfil_ingeniero import Especialidad
    return Especialidad.objects.create(
        codigo="T01",
        nombre="Taludes",
    )


@pytest.fixture
def tarifa_porcentaje_obra_taludes(db, tarifa_liquidacion_base_taludes, especialidad_taludes):
    """Create a TarifaPorcentajeObra for Taludes."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaPorcentajeObra,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_taludes,
        especialidad=especialidad_taludes,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_taludes_created(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_taludes,
    especialidad_taludes,
    tipo_taludes,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionTaludes + LiquidacionPorcentajeObra
    for testing the list endpoint.

    Note: igv_id and uit_id are passed as UUID strings (igv_vigente.id, uit_vigente.id)
    because the presenter (present_list) uses str(lg.igv_id) expecting a UUID string,
    not the IGV object's __str__ representation.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-TALUDES-2024-001",
        observacion="Test liquidation",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionTaludes (identity)
    taludes = LiquidacionTaludes.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorcentajeObra
    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite=None,
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    # Create LiquidacionPorcentajeObraDetalle
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_taludes,
        especialidad=especialidad_taludes,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
        igv=Decimal("180.00"),
        uit=Decimal("515.00"),
        total=Decimal("1180.00"),
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_endpoint_returns_200(
    auth_client,
    liquidacion_taludes_created,
):
    """
    GET /liquidaciones/taludes/ returns 200.
    """
    response = auth_client.get("/liquidaciones/taludes/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_response_has_paginated_data_structure(
    auth_client,
    liquidacion_taludes_created,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/taludes/")

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
def test_list_response_contains_liquidacion_taludes_output(
    auth_client,
    liquidacion_taludes_created,
):
    """
    Each item in items has the LiquidacionTaludesOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    response = auth_client.get("/liquidaciones/taludes/")

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
def test_list_pagination_params_work(auth_client, liquidacion_taludes_created):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/liquidaciones/taludes/?page=1&page_size=5")

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
    response = auth_client.get("/liquidaciones/taludes/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


@pytest.mark.django_db
def test_list_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_taludes_created,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    response = auth_client.get("/liquidaciones/taludes/")

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
    liquidacion_taludes_created,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    response = auth_client.get("/liquidaciones/taludes/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    le = item["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "valor_declarado" not in le, \
        "liquidacion_especifica should NOT have valor_declarado"


@pytest.mark.django_db
def test_list_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_taludes_created,
):
    """
    liquidacion_tipo wrapper has calculation fields: valor_declarado, detalles, etc.
    """
    response = auth_client.get("/liquidaciones/taludes/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt


@pytest.mark.django_db
def test_list_detalles_have_required_fields(
    auth_client,
    liquidacion_taludes_created,
):
    """
    Each detalle in liquidacion_tipo.detalles has required fields.
    """
    response = auth_client.get("/liquidaciones/taludes/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert len(lt["detalles"]) >= 1, "Should have at least 1 detalle"

    detalle = lt["detalles"][0]
    assert "id" in detalle
    assert "tarifa_aplicada_id" in detalle
    assert "especialidad_id" in detalle
    assert "porcentaje_aplicado" in detalle
    assert "subtotal" in detalle
    assert "igv" in detalle
    assert "uit" in detalle
    assert "total" in detalle
