"""
Integration tests for the Mecánica de Suelos /cotizar endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


@pytest.fixture
def ubigeo_departamento(db):
    """Create a department for testing."""
    return UbigeoDepartamento.objects.create(
        nombre="Lima",
    )


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    """Create a province for testing."""
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento,
        nombre="Lima",
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    """Create a district for testing."""
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia,
        nombre="Miraflores",
        ubigeo="150132",
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    """Create a municipalidad for testing."""
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


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


@pytest.fixture
def valid_tarifa_m2_id(tarifa_m2_ms):
    """Return the ID of the tariff as a string."""
    return str(tarifa_m2_ms.id)


@pytest.mark.django_db
def test_ms_cotizar_happy_path(api_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id, ubigeo_distrito):
    """
    POST with valid data returns 200 and correct structure.

    Validates that the /liquidaciones/mecanica-suelos/cotizar endpoint
    accepts a valid payload and returns 200 with the expected response.
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "datos" in result, "Result should have 'datos' key"
    assert "calculo" in result, "Result should have 'calculo' key"


@pytest.mark.django_db
def test_ms_cotizar_area_zero_returns_400(api_client, valid_tarifa_m2_id):
    """
    area_solicitada = 0 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for area=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ms_cotizar_area_negative_returns_400(api_client, valid_tarifa_m2_id):
    """
    area_solicitada = -10 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": -10,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for negative area, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ms_cotizar_response_has_correct_structure(api_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id, ubigeo_distrito):
    """
    Verify the output JSON has the correct cotizar structure with datos and calculo wrappers.

    Note: The /cotizar endpoint returns CotizarPorMetroCuadradoOutputSchema structure.
    The liquidacion_general wrapper is NOT part of this endpoint's response since
    it only handles the specific M2 calculation (cotizar), not the full primera revision.
    This test validates the structure that /cotizar actually returns.
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # The cotizar endpoint returns 'datos' and 'calculo' at the top level
    # These contain the tariff, derecho, and calculation results
    assert "datos" in result, "Response should have 'datos' wrapper"
    assert "calculo" in result, "Response should have 'calculo' wrapper"

    # datos contains entrada, tarifa, derecho, and variables_financieras
    datos = result["datos"]
    assert "tarifa" in datos, "datos should have 'tarifa' wrapper"
    assert "derecho" in datos, "datos should have 'derecho' wrapper"

    # Verify calculo has the expected calculation fields
    calculo = result["calculo"]
    assert "monto_bruto" in calculo, "calculo should have 'monto_bruto'"
    assert "subtotal" in calculo, "calculo should have 'subtotal'"
    assert "total" in calculo, "calculo should have 'total'"


@pytest.mark.django_db
def test_ms_cotizar_no_usuario_creador_in_input(api_client, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id):
    """
    Verify the orchestrator handles a payload that does NOT contain usuario_creador.

    The CotizarPorMetroCuadradoInputSchema does not require usuario_creador.
    The endpoint should work correctly without this field.
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 50.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    # Ensure usuario_creador is NOT in payload
    assert "usuario_creador" not in str(payload)

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200 without usuario_creador, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ms_cotizar_clamping_minimo(api_client, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id):
    """
    When area_solicitada is below derecho_minimo, the response should use derecho_minimo.

    derecho_minimo = 500.00, area_solicitada = 1.0, costo_por_m2 = 150
    total_bruto = 1.0 * 150 = 150 < 500, so clamp: total = 500
    subtotal = 500 / 1.18 = 423.73, igv = 500 - 423.73 = 76.27
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 1.0,  # Below derecho_minimo of 500.00
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    calculo = result["calculo"]

    # total is clamped to derecho_minimo (500.00)
    # subtotal is derived: total / 1.18 = 423.73
    assert float(calculo["total"]) == 500.00, f"Expected total to be clamped to 500.00, got {calculo['total']}"
    assert abs(float(calculo["subtotal"]) - 423.73) < 0.01, f"Expected subtotal ~423.73 (500/1.18), got {calculo['subtotal']}"
    # After fix: subtotal != total (IGV is derived, not part of the clamped total)
    assert float(calculo["total"]) != float(calculo["subtotal"]), "total should not equal subtotal after IGV derivation"


@pytest.mark.django_db
def test_ms_cotizar_clamping_maximo(api_client, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id):
    """
    When area_solicitada is above derecho_maximo, the response should use derecho_maximo.

    derecho_maximo = 50000.00, area_solicitada = 100000.0, costo_por_m2 = 150
    total_bruto = 100000 * 150 = 15,000,000 > 50000, so clamp: total = 50000
    subtotal = 50000 / 1.18 = 42372.88, igv = 50000 - 42372.88 = 7627.12
    """
    payload = {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100000.0,  # Above derecho_maximo of 50000.00
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = api_client.post(
        "/liquidaciones/mecanica-suelos/cotizar",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    calculo = result["calculo"]

    # total is clamped to derecho_maximo (50000.00)
    # subtotal is derived: 50000 / 1.18 = 42372.88
    assert float(calculo["total"]) == 50000.00, f"Expected total to be clamped to 50000.00, got {calculo['total']}"
    assert abs(float(calculo["subtotal"]) - 42372.88) < 0.01, f"Expected subtotal ~42372.88 (50000/1.18), got {calculo['subtotal']}"
    # After fix: subtotal != total (IGV is derived, not part of the clamped total)
    assert float(calculo["total"]) != float(calculo["subtotal"]), "total should not equal subtotal after IGV derivation"
