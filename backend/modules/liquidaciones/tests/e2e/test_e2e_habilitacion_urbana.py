"""
E2E flow tests for Habilitación Urbana (HU).

Mimics the real frontend flow:
1. GET tarifas vigentes -> extract tarifa_id
2. POST crear liquidacion with extracted tarifa_id

Uses absolute imports with Django settings: config.settings.development
Uses ninja.testing.TestClient + JWT authentication.
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from django.contrib.auth import get_user_model

from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    """Create a department for testing."""
    return UbigeoDepartamento.objects.create(nombre="LIMA")


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
def igv_vigente(db):
    """Create an IGV vigente for testing."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    """Create a UIT vigente for testing."""
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_liquidacion_base_hu(db):
    """Create a TarifaLiquidacionBase for Habilitación Urbana."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tarifa_liquidacion_base_hu):
    """Create a TarifaPorMetroCuadrado for Habilitación Urbana."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_hu,
        costo_por_m2=Decimal("120.0000"),
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
def create_user(db):
    """Create a test user for JWT authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_e2e_hu",
        email="test_e2e_hu@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints."""
    return TestClient(api)


@pytest.fixture
def auth_client(api_client, create_user):
    """Authenticate the test client using JWT token."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


# ── E2E Test ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_e2e_habilitacion_urbana_flow(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_m2_hu, derecho_m2_vigente, ubigeo_distrito
):
    """
    E2E flow for Habilitación Urbana:

    1. GET /liquidaciones/habilitacion-urbana/tarifas/vigentes
    2. Extract tarifa_id from response
    3. POST /liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision
       with extracted tarifa_id
    4. Assert 200 OK and liquidacion_general + liquidacion_especifica in response
    """
    # Step 1: GET tarifas vigentes
    response = auth_client.get("/liquidaciones/habilitacion-urbana/tarifas/vigentes")

    assert response.status_code == 200, \
        f"Expected 200 from GET tarifas vigentes, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "tarifa_vigente" in result, "Result should have 'tarifa_vigente'"
    assert "derecho_vigente" in result, "Result should have 'derecho_vigente'"

    # Step 2: Extract tarifa_id from response
    tarifa_id = result["tarifa_vigente"]["datos"]["id"]
    assert tarifa_id is not None, "tarifa_id should not be None"

    municipalidad_id = str(municipalidad.id)
    distrito_id = str(ubigeo_distrito.id)

    # Step 3: Construct payload using extracted tarifa_id
    payload = {
        "liquidacion_general": {
            "municipalidad_id": municipalidad_id,
            "expediente": "EXP-E2E-HU-2024-001",
            "observacion": "E2E test Habilitación Urbana",
            "proyecto": {
                "denominacion": "Proyecto E2E HU Test",
                "nombre_propietario": "Propietario E2E HU SAC",
                "direccion": "Av. E2E 123, Lima",
                "distrito_id": distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Propietario E2E HU SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 150.0,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_id),
            },
        },
    }

    # Step 4: POST crear liquidacion
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200 from POST crear liquidacion, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]

    # Assert liquidacion_general is in response
    assert "liquidacion_general" in result, \
        "Result should have 'liquidacion_general' wrapper"
    lg = result["liquidacion_general"]
    assert "id" in lg, "liquidacion_general should have 'id'"
    assert lg["expediente"] == "EXP-E2E-HU-2024-001", \
        f"Expected expediente 'EXP-E2E-HU-2024-001', got {lg['expediente']}"
    assert lg["numero_revision"] == 1, \
        f"Expected numero_revision=1, got {lg['numero_revision']}"

    # Assert liquidacion_especifica is in response
    assert "liquidacion_especifica" in result, \
        "Result should have 'liquidacion_especifica' wrapper"
    le = result["liquidacion_especifica"]
    assert "id" in le, "liquidacion_especifica should have 'id'"
    assert "numero" in le, "liquidacion_especifica should have 'numero'"

    # Assert liquidacion_tipo is in response (calculation wrapper)
    assert "liquidacion_tipo" in result, \
        "Result should have 'liquidacion_tipo' wrapper"
    lt = result["liquidacion_tipo"]
    assert "id" in lt, "liquidacion_tipo should have 'id'"
    assert "area_m2" in lt, "liquidacion_tipo should have 'area_m2'"
    assert "costo_por_m2" in lt, "liquidacion_tipo should have 'costo_por_m2'"

    # Verify calculations: area=150, costo_por_m2=120, subtotal=18000
    assert lg["sub_total"] == 18000.0, \
        f"Expected sub_total=18000.0 (150 * 120), got {lg['sub_total']}"
