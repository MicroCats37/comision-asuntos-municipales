"""
Integration tests for the Mecánica de Suelos /tarifas/vigentes endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from config.api import api
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


@pytest.fixture
def tarifa_liquidacion_base_ms(db, tipo_mecanica_suelos):
    """Create a TarifaLiquidacionBase for Mecánica de Suelos."""
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_liquidacion_base_ms):
    """Create a TarifaPorMetroCuadrado for Mecánica de Suelos."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_ms,
        costo_por_m2=Decimal("150.0000"),
    )


@pytest.fixture
def derecho_m2_vigente(db):
    """Create a DerechoPorMetroCuadrado vigente for testing."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.mark.django_db
def test_ms_tarifas_vigentes_exitoso(api_client, tarifa_m2_ms, derecho_m2_vigente):
    """
    GET /tarifas/vigentes returns 200 with active tariff and derecho data.

    When there is an active tariff and derecho for Mecánica de Suelos,
    the endpoint should return them in the response.
    """
    response = api_client.get("/liquidaciones/mecanica-suelos/tarifas/vigentes")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "tarifa_vigente" in result, "Result should have 'tarifa_vigente' wrapper"
    assert "derecho_vigente" in result, "Result should have 'derecho_vigente' wrapper"

    # Verify tarifa_vigente structure
    tarifa_vigente = result["tarifa_vigente"]
    assert "datos" in tarifa_vigente, "tarifa_vigente should have 'datos' wrapper"
    assert "id" in tarifa_vigente["datos"], "tarifa_vigente.datos should have 'id'"
    assert "costo_por_m2" in tarifa_vigente["datos"], "tarifa_vigente.datos should have 'costo_por_m2'"
    assert Decimal(str(tarifa_vigente["datos"]["costo_por_m2"])) == Decimal("150.0"), "tarifa_vigente.costo_por_m2 should be 150.0"

    # Verify derecho_vigente structure
    derecho_vigente = result["derecho_vigente"]
    assert "datos" in derecho_vigente, "derecho_vigente should have 'datos' wrapper"
    assert "id" in derecho_vigente["datos"], "derecho_vigente.datos should have 'id'"
    assert "derecho_minimo" in derecho_vigente["datos"], "derecho_vigente.datos should have 'derecho_minimo'"
    assert "derecho_maximo" in derecho_vigente["datos"], "derecho_vigente.datos should have 'derecho_maximo'"
    assert Decimal(str(derecho_vigente["datos"]["derecho_minimo"])) == Decimal("500.0"), "derecho_minimo should be 500.0"
    assert Decimal(str(derecho_vigente["datos"]["derecho_maximo"])) == Decimal("50000.0"), "derecho_maximo should be 50000.0"


@pytest.mark.django_db
def test_ms_tarifas_vigentes_filtro_tipo(api_client, db, tipo_habilitacion_urbana, tipo_mecanica_suelos):
    """
    Verify that /tarifas/vigentes for MS only returns MS tariffs, not HU tariffs.

    Creates a HU tariff and verifies MS endpoint doesn't return it.
    """
    # Create HU tariff
    
    hu_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    hu_tarifa = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=hu_tarifa_base,
        costo_por_m2=Decimal("200.0000"),  # Different price than MS
    )

    # Create MS tariff
    
    ms_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    ms_tarifa = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=ms_tarifa_base,
        costo_por_m2=Decimal("150.0000"),
    )

    # Create derecho
    derecho = DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    response = api_client.get("/liquidaciones/mecanica-suelos/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # Should only return MS tariff (150.0), not HU tariff (200.0)
    assert Decimal(str(result["tarifa_vigente"]["datos"]["costo_por_m2"])) == Decimal("150.0"), \
        "Should return MS tariff (150.0), not HU tariff (200.0)"


@pytest.mark.django_db
def test_ms_tarifas_vigentes_returns_uuid_not_none(api_client, tarifa_m2_ms, derecho_m2_vigente):
    """
    Verify that the IDs returned are valid UUIDs, not None.

    The tariff and derecho IDs should be valid UUIDs for FK relationships.
    """
    response = api_client.get("/liquidaciones/mecanica-suelos/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # Verify IDs are present and are valid UUIDs (not None)
    # JSON deserialization returns UUIDs as str, so we explicitly convert to validate
    tarifa_id_str = result["tarifa_vigente"]["datos"]["id"]
    assert tarifa_id_str is not None, "tarifa_vigente.id should not be None"
    tarifa_id = uuid.UUID(str(tarifa_id_str))
    assert isinstance(tarifa_id, uuid.UUID), f"tarifa_vigente.id should be valid UUID, got {type(tarifa_id)}"

    derecho_id_str = result["derecho_vigente"]["datos"]["id"]
    assert derecho_id_str is not None, "derecho_vigente.id should not be None"
    derecho_id = uuid.UUID(str(derecho_id_str))
    assert isinstance(derecho_id, uuid.UUID), f"derecho_vigente.id should be valid UUID, got {type(derecho_id)}"
