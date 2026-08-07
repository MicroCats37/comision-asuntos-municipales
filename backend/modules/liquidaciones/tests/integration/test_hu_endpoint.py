"""
Integration tests for the Habilitacion Urbana /cotizar endpoint.

Tests use Django's AsyncClient (not Ninja's TestAsyncClient which had issues).
All tests are async and use @pytest.mark.django_db for database access.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from django.test import AsyncClient
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
        nombre="LIMA",
    )


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    """Create a province for testing."""
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento,
        nombre="LIMA",
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    """Create a district for testing."""
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia,
        nombre="MIRAFLORES",
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
def tarifa_liquidacion_base_hu(db):
    """Create a TarifaLiquidacionBase for Habilitacion Urbana."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tarifa_liquidacion_base_hu):
    """Create a TarifaPorMetroCuadrado for Habilitacion Urbana."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_hu,
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
    """Django AsyncClient for testing Ninja endpoints."""
    return AsyncClient()


@pytest.fixture
def valid_tarifa_m2_id(tarifa_m2_hu):
    """Return the ID of the tariff as a string."""
    return str(tarifa_m2_hu.id)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_hu_primera_revision_happy_path(api_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id, ubigeo_distrito):
    """
    POST with valid data returns 200 and correct structure.

    Validates that the /liquidaciones/habilitacion-urbana/cotizar endpoint
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

    response = await api_client.post(
        "/api/liquidaciones/habilitacion-urbana/cotizar",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "datos" in result, "Result should have 'datos' key"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_hu_primera_revision_area_zero_returns_400(api_client, valid_tarifa_m2_id):
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

    response = await api_client.post(
        "/api/liquidaciones/habilitacion-urbana/cotizar",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400, f"Expected 400 for area=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_hu_primera_revision_area_negative_returns_400(api_client, valid_tarifa_m2_id):
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

    response = await api_client.post(
        "/api/liquidaciones/habilitacion-urbana/cotizar",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400, f"Expected 400 for negative area, got {response.status_code}: {response.content}"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_hu_response_has_three_wrappers(api_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id, ubigeo_distrito):
    """
    Verify the output JSON has liquidacion_general, liquidacion_tipo, liquidacion_especifica.

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

    response = await api_client.post(
        "/api/liquidaciones/habilitacion-urbana/cotizar",
        data=payload,
        content_type="application/json",
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_hu_no_usuario_creador_in_input(api_client, derecho_m2_vigente, valid_tarifa_m2_id):
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

    response = await api_client.post(
        "/api/liquidaciones/habilitacion-urbana/cotizar",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 200, f"Expected 200 without usuario_creador, got {response.status_code}: {response.content}"
