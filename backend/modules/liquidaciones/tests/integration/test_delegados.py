"""
Integration tests for Delegados endpoints.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /delegados/ returns 200 with PaginatedData structure
- GET /delegados/{id}/municipalidades returns 200 with vigencia status
- GET /delegados/municipalidad/{id}?vigente=true filters correctly
- Pagination params work
- Empty list returns empty items array

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, etc.).
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
)
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
from modules.entidades.domain.models.municipalidad import Municipalidad


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def perfil_ingeniero_delegado(db):
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
def perfil_ingeniero_delegado_2(db):
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
def delegado(db, perfil_ingeniero_delegado):
    """Create a Delegado for testing."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado,
    )


@pytest.fixture
def delegado_2(db, perfil_ingeniero_delegado_2):
    """Create a second Delegado for testing."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado_2,
    )


@pytest.fixture
def municipalidad_delegado(db, municipalidad, delegado):
    """Delegado-Municipalidad assignment for the first delegado."""
    return DelegadoMunicipalidad.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo="TITULAR",
    )


@pytest.fixture
def municipalidad_delegado_periodo_vigente(db, municipalidad_delegado):
    """Create a vigente periodo for municipalidad_delegado."""
    return DelegadoMunicipalidadPeriodo.objects.create(
        delegado_municipalidad=municipalidad_delegado,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )


@pytest.fixture
def municipalidad_delegado_2(db, municipalidad, delegado_2):
    """Delegado-Municipalidad assignment for the second delegado."""
    return DelegadoMunicipalidad.objects.create(
        delegado=delegado_2,
        municipalidad=municipalidad,
        tipo="ALTERNO",
    )


@pytest.fixture
def municipalidad_delegado_2_periodo_pasado(db, municipalidad_delegado_2):
    """Create a past (non-vigente) periodo for municipalidad_delegado_2."""
    return DelegadoMunicipalidadPeriodo.objects.create(
        delegado_municipalidad=municipalidad_delegado_2,
        periodo_inicio=date.today() - timedelta(days=365),
        periodo_fin=date.today() - timedelta(days=30),
    )


# ── Tests: GET /delegados/ ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_delegados_returns_200(
    auth_client,
    delegado,
):
    """
    GET /delegados/ returns 200.
    """
    response = auth_client.get("/delegados/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_delegados_has_paginated_data_structure(
    auth_client,
    delegado,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/delegados/")

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
def test_list_delegados_contains_delegado_output(
    auth_client,
    delegado,
):
    """
    Each item in items has the DelegadoOut structure.
    """
    response = auth_client.get("/delegados/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["items"]) >= 1, "Should have at least 1 item"

    item = result["items"][0]
    assert "id" in item, "Item should have 'id'"
    assert "perfil_ingeniero" in item, "Item should have 'perfil_ingeniero'"


@pytest.mark.django_db
def test_list_delegados_perfil_ingeniero_has_expected_fields(
    auth_client,
    delegado,
):
    """
    perfil_ingeniero wrapper has expected fields.
    """
    response = auth_client.get("/delegados/")

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
def test_list_delegados_pagination_params_work(
    auth_client,
    delegado,
    delegado_2,
):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/delegados/?page=1&page_size=1")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 1
    assert result["total"] >= 1
    assert result["total_pages"] >= 1
    assert len(result["items"]) == 1


@pytest.mark.django_db
def test_list_delegados_empty_returns_empty_items(auth_client, db):
    """
    When no delegados exist, returns empty items array with total=0.
    """
    response = auth_client.get("/delegados/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


# ── Tests: GET /delegados/{id}/municipalidades ─────────────────────────────────

@pytest.mark.django_db
def test_municipalidades_returns_200(
    auth_client,
    delegado,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
):
    """
    GET /delegados/{delegado_id}/municipalidades returns 200.
    """
    response = auth_client.get(f"/delegados/{delegado.id}/municipalidades")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_municipalidades_response_has_correct_structure(
    auth_client,
    delegado,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
):
    """
    Response has the DelegadoMunicipalidadesOut structure.
    """
    response = auth_client.get(f"/delegados/{delegado.id}/municipalidades")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data

    result = data["data"]
    assert "delegado_id" in result
    assert "perfil_ingeniero" in result
    assert "municipalidades" in result
    assert isinstance(result["municipalidades"], list)


@pytest.mark.django_db
def test_municipalidades_includes_vigencia_status(
    auth_client,
    delegado,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
):
    """
    The municipalidades list includes es_vigente, periodo_inicio, periodo_fin.
    """
    response = auth_client.get(f"/delegados/{delegado.id}/municipalidades")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["municipalidades"]) >= 1
    mun = result["municipalidades"][0]
    assert "es_vigente" in mun
    assert "periodo_inicio" in mun
    assert "periodo_fin" in mun
    assert "tipo" in mun


@pytest.mark.django_db
def test_municipalidades_not_found_returns_404(
    auth_client,
):
    """
    GET /delegados/{non_existent_id}/municipalidades returns 404.
    """
    fake_uuid = uuid.uuid4()
    response = auth_client.get(f"/delegados/{fake_uuid}/municipalidades")

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"


# ── Tests: GET /delegados/municipalidad/{id} ───────────────────────────────────

@pytest.mark.django_db
def test_delegados_por_municipalidad_returns_200(
    auth_client,
    municipalidad,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
):
    """
    GET /delegados/municipalidad/{municipalidad_id} returns 200.
    """
    response = auth_client.get(f"/delegados/municipalidad/{municipalidad.id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_delegados_por_municipalidad_has_paginated_data_structure(
    auth_client,
    municipalidad,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
):
    """
    Response has the PaginatedData structure.
    """
    response = auth_client.get(f"/delegados/municipalidad/{municipalidad.id}")

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
def test_delegados_por_municipalidad_vigente_filter_returns_only_vigentes(
    auth_client,
    municipalidad,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
    municipalidad_delegado_2,
    municipalidad_delegado_2_periodo_pasado,
):
    """
    GET /delegados/municipalidad/{id}?vigente=true returns only vigentes.
    """
    response = auth_client.get(f"/delegados/municipalidad/{municipalidad.id}?vigente=true")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["total"] >= 1
    for item in result["items"]:
        assert item["es_vigente"] is True, \
            "When vigente=true, all items should have es_vigente=True"


@pytest.mark.django_db
def test_delegados_por_municipalidad_vigente_false_filter(
    auth_client,
    municipalidad,
    municipalidad_delegado,
    municipalidad_delegado_periodo_vigente,
    municipalidad_delegado_2,
    municipalidad_delegado_2_periodo_pasado,
):
    """
    GET /delegados/municipalidad/{id}?vigente=false returns only non-vigentes.
    """
    response = auth_client.get(f"/delegados/municipalidad/{municipalidad.id}?vigente=false")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    result = data["data"]

    for item in result["items"]:
        assert item["es_vigente"] is False, \
            "When vigente=false, all items should have es_vigente=False"


@pytest.mark.django_db
def test_delegados_por_municipalidad_empty_result(
    auth_client,
    db,
):
    """
    When no delegados exist for a municipalidad, returns empty items.
    """
    fake_uuid = uuid.uuid4()
    response = auth_client.get(f"/delegados/municipalidad/{fake_uuid}")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
