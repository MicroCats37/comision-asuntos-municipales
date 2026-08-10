"""
Integration tests for Finanzas GET /variables/vigentes endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from config.api import api
from modules.finanzas.domain.models import IGV, UIT


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.fixture
def igv_vigente(db):
    """Create a vigente IGV for testing."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    """Create a vigente UIT for testing."""
    return UIT.objects.create(
        valor=5150,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.mark.django_db
def test_returns_200_with_vigentes_variables(
    api_client, igv_vigente, uit_vigente
):
    """
    GET /variables/vigentes returns 200 and valid schema.

    When there are active IGV and UIT, the endpoint should return them
    with the correct structure.
    """
    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "success" in data, "Response should have 'success' key"
    assert data["success"] is True, "Response success should be True"
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "igv_valor" in result, "Result should have 'igv_valor'"
    assert "igv_periodo_inicio" in result, "Result should have 'igv_periodo_inicio'"
    assert "uit_valor" in result, "Result should have 'uit_valor'"
    assert "uit_periodo_inicio" in result, "Result should have 'uit_periodo_inicio'"


@pytest.mark.django_db
def test_returns_correct_igv_valor(api_client, igv_vigente, uit_vigente):
    """
    Response contains the correct IGV valor.
    """
    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["igv_valor"] == 0.18, \
        f"Expected igv_valor 0.18, got {result['igv_valor']}"


@pytest.mark.django_db
def test_returns_correct_uit_valor(api_client, igv_vigente, uit_vigente):
    """
    Response contains the correct UIT valor.
    """
    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["uit_valor"] == 5150.0, \
        f"Expected uit_valor 5150.0, got {result['uit_valor']}"


@pytest.mark.django_db
def test_returns_correct_periodo_inicio(api_client, igv_vigente, uit_vigente):
    """
    Response contains the correct periodo_inicio dates in ISO format.
    """
    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["igv_periodo_inicio"] == "2024-01-01", \
        f"Expected igv_periodo_inicio '2024-01-01', got {result['igv_periodo_inicio']}"
    assert result["uit_periodo_inicio"] == "2024-01-01", \
        f"Expected uit_periodo_inicio '2024-01-01', got {result['uit_periodo_inicio']}"


@pytest.mark.django_db
def test_returns_zeros_when_no_vigentes(api_client, db):
    """
    When no IGV or UIT are vigentes, returns zero values.
    """
    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["igv_valor"] == 0.0, \
        f"Expected igv_valor 0.0 when no vigente, got {result['igv_valor']}"
    assert result["uit_valor"] == 0.0, \
        f"Expected uit_valor 0.0 when no vigente, got {result['uit_valor']}"


@pytest.mark.django_db
def test_excludes_expired_igv(api_client, db, uit_vigente):
    """
    Only vigentes IGV returned (not expired).
    """
    # Create expired IGV
    expired_igv = IGV.objects.create(
        valor=Decimal("0.17"),
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 12, 31),
    )

    # Create vigente IGV
    vigente_igv = IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["igv_valor"] == 0.18, \
        f"Expected igv_valor 0.18 (vigente), got {result['igv_valor']}"


@pytest.mark.django_db
def test_excludes_expired_uit(api_client, db, igv_vigente):
    """
    Only vigentes UIT returned (not expired).
    """
    # Create expired UIT
    expired_uit = UIT.objects.create(
        valor=5000,
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 12, 31),
    )

    # Create vigente UIT
    vigente_uit = UIT.objects.create(
        valor=5150,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    response = api_client.get("/finanzas/variables/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["uit_valor"] == 5150.0, \
        f"Expected uit_valor 5150.0 (vigente), got {result['uit_valor']}"
