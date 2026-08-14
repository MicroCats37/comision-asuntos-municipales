"""
Integration tests for Inspectores endpoints.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /inspectores/ returns 200 with PaginatedData structure
- GET /inspectores/{id} returns 200 with detail
- GET /inspectores/{id} returns 404 for non-existent
- GET /inspectores/vigentes?tipo_liquidacion=X returns only vigentes
- Pagination params work
- Empty list returns empty items array

Fixtures are shared via conftest.py.
"""
import pytest
from datetime import date, timedelta
import uuid

from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorAsignacionPeriodo,
    InspectorTipoLiquidacion,
)
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def perfil_ingeniero_inspector(db):
    """Create a PerfilIngeniero for testing."""
    return PerfilIngeniero.objects.create(
        cip="12345",
        dni="76543210",
        nombres="Juan",
        apellido_paterno="Perez",
        apellido_materno="Garcia",
        correo_personal="juan.perez@test.com",
    )


@pytest.fixture
def perfil_ingeniero_inspector_2(db):
    """Create a second PerfilIngeniero for testing."""
    return PerfilIngeniero.objects.create(
        cip="54321",
        dni="87654321",
        nombres="Maria",
        apellido_paterno="Lopez",
        apellido_materno="Rodriguez",
        correo_personal="maria.lopez@test.com",
    )


@pytest.fixture
def inspector_edificacion(db, perfil_ingeniero_inspector, tipo_edificacion):
    """Create an Inspector for Edificacion testing."""
    inspector = Inspector.objects.create(
        perfil_ingeniero=perfil_ingeniero_inspector,
    )
    InspectorTipoLiquidacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,
        numero_registro="REG-001-EDIF",
        telefono="999888777",
        email="juan.perez@test.com",
    )
    return inspector


@pytest.fixture
def inspector_habilitacion_urbana(db, perfil_ingeniero_inspector_2, tipo_habilitacion_urbana):
    """Create an Inspector for Habilitacion Urbana testing."""
    inspector = Inspector.objects.create(
        perfil_ingeniero=perfil_ingeniero_inspector_2,
    )
    InspectorTipoLiquidacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_registro="REG-002-HU",
        telefono="999888666",
        email="maria.lopez@test.com",
    )
    return inspector


@pytest.fixture
def inspector_periodo_vigente(db, inspector_edificacion):
    """Create a vigente InspectorAsignacionPeriodo for the inspector."""
    return InspectorAsignacionPeriodo.objects.create(
        inspector_tipo_liquidacion=inspector_edificacion.tipos_liquidacion.first(),
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )


@pytest.fixture
def inspector_periodo_pasado(db, inspector_habilitacion_urbana):
    """Create a past (non-vigente) InspectorAsignacionPeriodo."""
    return InspectorAsignacionPeriodo.objects.create(
        inspector_tipo_liquidacion=inspector_habilitacion_urbana.tipos_liquidacion.first(),
        periodo_inicio=date.today() - timedelta(days=365),
        periodo_fin=date.today() - timedelta(days=30),
    )


# ── Tests: GET /inspectores/ ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_inspectores_returns_200(
    auth_client,
    inspector_edificacion,
):
    """
    GET /inspectores/ returns 200.
    """
    response = auth_client.get("/inspectores/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_inspectores_has_paginated_data_structure(
    auth_client,
    inspector_edificacion,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/inspectores/")

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
def test_list_inspectores_contains_inspector_output(
    auth_client,
    inspector_edificacion,
):
    """
    Each item in items has the InspectorOut structure.
    """
    response = auth_client.get("/inspectores/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["items"]) >= 1, "Should have at least 1 item"

    item = result["items"][0]
    assert "id" in item, "Item should have 'id'"
    assert "tipo_liquidacion" in item, "Item should have 'tipo_liquidacion'"
    assert "numero_registro" in item, "Item should have 'numero_registro'"
    assert "perfil_ingeniero" in item, "Item should have 'perfil_ingeniero'"


@pytest.mark.django_db
def test_list_inspectores_perfil_ingeniero_has_expected_fields(
    auth_client,
    inspector_edificacion,
):
    """
    perfil_ingeniero wrapper has expected fields.
    """
    response = auth_client.get("/inspectores/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    pi = item["perfil_ingeniero"]

    assert "id" in pi
    assert "cip" in pi
    assert "dni" in pi
    assert "nombres" in pi
    assert "apellido_paterno" in pi
    assert "apellido_materno" in pi
    assert "nombre_completo" in pi


@pytest.mark.django_db
def test_list_inspectores_pagination_params_work(
    auth_client,
    inspector_edificacion,
    inspector_habilitacion_urbana,
):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/inspectores/?page=1&page_size=1")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 1
    assert result["total"] == 2
    assert result["total_pages"] == 2
    assert len(result["items"]) == 1


@pytest.mark.django_db
def test_list_inspectores_empty_returns_empty_items(auth_client, db):
    """
    When no inspectores exist, returns empty items array with total=0.
    """
    response = auth_client.get("/inspectores/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


# ── Tests: GET /inspectores/{id} ───────────────────────────────────────────────

@pytest.mark.django_db
def test_obtener_inspector_returns_200(
    auth_client,
    inspector_edificacion,
):
    """
    GET /inspectores/{id} returns 200.
    """
    response = auth_client.get(f"/inspectores/{inspector_edificacion.id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_obtener_inspector_has_correct_structure(
    auth_client,
    inspector_edificacion,
):
    """
    Response has the InspectorDetailOut structure.
    """
    response = auth_client.get(f"/inspectores/{inspector_edificacion.id}")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data

    result = data["data"]
    assert "id" in result
    assert "tipo_liquidacion" in result
    assert "numero_registro" in result
    assert "telefono" in result
    assert "email" in result
    assert "perfil_ingeniero" in result


@pytest.mark.django_db
def test_obtener_inspector_not_found_returns_404(
    auth_client,
):
    """
    GET /inspectores/{non_existent_id} returns 404.
    """
    fake_uuid = uuid.uuid4()
    response = auth_client.get(f"/inspectores/{fake_uuid}")

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"


# ── Tests: GET /inspectores/vigentes ──────────────────────────────────────────

@pytest.mark.django_db
def test_list_inspectores_vigentes_returns_200(
    auth_client,
    inspector_edificacion,
    inspector_periodo_vigente,
):
    """
    GET /inspectores/vigentes?tipo_liquidacion=EDIFICACION returns 200.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.EDIFICACION}"
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_inspectores_vigentes_has_paginated_data_structure(
    auth_client,
    inspector_edificacion,
    inspector_periodo_vigente,
):
    """
    Response has the PaginatedData structure.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.EDIFICACION}"
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data

    result = data["data"]
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert "total_pages" in result


@pytest.mark.django_db
def test_list_inspectores_vigentes_returns_only_vigentes(
    auth_client,
    inspector_edificacion,
    inspector_periodo_vigente,
    inspector_habilitacion_urbana,
    inspector_periodo_pasado,
):
    """
    GET /inspectores/vigentes?tipo_liquidacion=EDIFICACION returns only vigentes.
    Only inspector_edificacion has a vigente periodo.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.EDIFICACION}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Should have at least 1 item (inspector_edificacion)
    assert result["total"] >= 1
    for item in result["items"]:
        assert item["es_vigente"] is True, \
            "All items should have es_vigente=True"
        assert item["tipo_liquidacion"] == TipoLiquidacion.EDIFICACION


@pytest.mark.django_db
def test_list_inspectores_vigentes_filters_by_tipo_liquidacion(
    auth_client,
    inspector_edificacion,
    inspector_periodo_vigente,
    inspector_habilitacion_urbana,
    inspector_periodo_pasado,
):
    """
    GET /inspectores/vigentes?tipo_liquidacion=HABILITACION_URBANA
    should return inspectors with that tipo_liquidacion.
    The inspector_habilitacion_urbana has a past (non-vigente) periodo,
    so it should NOT appear in vigentes.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.HABILITACION_URBANA}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # inspector_habilitacion_urbana has a PAST periodo, not vigente
    # So this should return 0 items (since inspector_periodo_pasado is not vigente)
    assert result["total"] == 0, \
        "HABILITACION_URBANA inspector has past periodo, should not be vigente"


@pytest.mark.django_db
def test_list_inspectores_vigentes_empty_result(
    auth_client,
    db,
):
    """
    When no vigentes inspectores exist for a tipo_liquidacion, returns empty items.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.EDIFICACION}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.django_db
def test_list_inspectores_vigentes_pagination_params_work(
    auth_client,
    inspector_edificacion,
    inspector_periodo_vigente,
):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get(
        f"/inspectores/vigentes?tipo_liquidacion={TipoLiquidacion.EDIFICACION}&page=1&page_size=1"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 1
