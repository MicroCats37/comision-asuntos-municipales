"""
Integration tests for the Habilitacion Urbana /nueva-liquidacion/primera-revision endpoint.

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
def create_user(db):
    """Create a test user (needed for FK to usuarios_usuario on LiquidacionGeneral)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    """Authenticate the test client using JWT token."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    """Create a municipalidad for testing."""
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def tarifa_liquidacion_base_hu(db, tipo_habilitacion_urbana):
    """Create a TarifaLiquidacionBase for Habilitacion Urbana."""
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
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
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.fixture
def valid_tarifa_m2_id(tarifa_m2_hu):
    """Return the ID of the tariff as a string."""
    return str(tarifa_m2_hu.id)


@pytest.fixture
def valid_municipalidad_id(municipalidad):
    """Return the ID of the municipalidad as a string."""
    return str(municipalidad.id)


@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    """Return the ID of the distrito as a string."""
    return str(ubigeo_distrito.id)


@pytest.fixture
def valid_payload(valid_municipalidad_id, valid_tarifa_m2_id, valid_distrito_id):
    """Return a valid full payload for primera-revision endpoint."""
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-001",
            "observacion": "Test observation",
            "proyecto": {
                "denominacion": "Proyecto de Habilitacion Urbana Test",
                "nombre_propietario": "Propietario Test SAC",
                "direccion": "Av. Test 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Propietario Test SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }


@pytest.mark.django_db
def test_hu_nueva_liquidacion_happy_path(
    auth_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    POST with valid data returns 200 and verifies the 3 wrappers.

    The /nueva-liquidacion/primera-revision endpoint accepts a valid full payload
    (liquidacion_general + liquidacion_especifica) and returns 200 with
    liquidacion_general, liquidacion_tipo, and liquidacion_especifica in the response.
    """
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "liquidacion_general" in result, "Result should have 'liquidacion_general' wrapper"
    assert "liquidacion_tipo" in result, "Result should have 'liquidacion_tipo' wrapper"
    assert "liquidacion_especifica" in result, "Result should have 'liquidacion_especifica' wrapper"

    # Verify liquidacion_general has expected fields
    lg = result["liquidacion_general"]
    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert lg["expediente"] == "EXP-2024-001"
    assert lg["numero_revision"] == 1

    # Verify liquidacion_tipo has M2 calculation fields (semantically: tipo = calculation)
    lt = result["liquidacion_tipo"]
    assert "id" in lt
    assert "area_m2" in lt
    assert "costo_por_m2" in lt

    # Verify liquidacion_especifica has identity fields (semantically: especifica = identity)
    le = result["liquidacion_especifica"]
    assert "id" in le
    assert "numero" in le


@pytest.mark.django_db
def test_hu_nueva_liquidacion_area_zero_returns_400(
    auth_client, valid_municipalidad_id, valid_tarifa_m2_id, valid_distrito_id
):
    """
    area_solicitada = 0 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-002",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 456",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789013",
                    "razon_social": "Propietario Test EIRL",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for area=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_hu_nueva_liquidacion_area_negative_returns_400(
    auth_client, valid_municipalidad_id, valid_tarifa_m2_id, valid_distrito_id
):
    """
    area_solicitada < 0 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-003",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test 2",
                "nombre_propietario": "Propietario Test 2",
                "direccion": "Av. Test 789",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789014",
                    "razon_social": "Propietario Test 2 EIRL",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": -10,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for negative area, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_hu_nueva_liquidacion_response_has_three_wrappers(
    auth_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify the output JSON has liquidacion_general, liquidacion_tipo, and liquidacion_especifica.

    The primera-revision endpoint returns LiquidacionHabilitacionUrbanaOutput which
    is the union of the three wrappers, unlike /cotizar which only returns M2 data.
    """
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # Validate all three top-level wrappers are present
    assert "liquidacion_general" in result, "Response should have 'liquidacion_general' wrapper"
    assert "liquidacion_tipo" in result, "Response should have 'liquidacion_tipo' wrapper"
    assert "liquidacion_especifica" in result, "Response should have 'liquidacion_especifica' wrapper"

    # Validate liquidacion_tipo structure (M2 calculation wrapper after semantic fix)
    lt = result["liquidacion_tipo"]
    assert "id" in lt, "liquidacion_tipo should have 'id'"
    assert "area_m2" in lt, "liquidacion_tipo should have 'area_m2'"
    assert "costo_por_m2" in lt, "liquidacion_tipo should have 'costo_por_m2'"
    assert "derecho_minimo" in lt, "liquidacion_tipo should have 'derecho_minimo'"
    assert "derecho_maximo" in lt, "liquidacion_tipo should have 'derecho_maximo'"
    assert "tarifa_aplicada_id" in lt, "liquidacion_tipo should have 'tarifa_aplicada_id'"
    assert "derecho_aplicado_id" in lt, "liquidacion_tipo should have 'derecho_aplicado_id'"

    # Validate liquidacion_especifica structure (identity wrapper after semantic fix)
    le = result["liquidacion_especifica"]
    assert "id" in le, "liquidacion_especifica should have 'id'"
    assert "numero" in le, "liquidacion_especifica should have 'numero'"


@pytest.mark.django_db
def test_hu_nueva_liquidacion_no_usuario_creador_in_input(
    auth_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    Verify the endpoint handles a payload that does NOT contain usuario_creador.

    The primera-revision endpoint should work correctly without usuario_creador in
    the input payload (usuario_id is hardcoded in the controller or extracted from token).
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-004",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Sin Usuario Creador",
                "nombre_propietario": "Prop Test",
                "direccion": "Calle Falsa 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "DNI",
                    "numero_documento": "12345678",
                    "razon_social": "Prop Test",
                },
            },
        },
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

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200 without usuario_creador, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert "liquidacion_general" in result
    assert "liquidacion_tipo" in result
    assert "liquidacion_especifica" in result


# ── denominacion_de_proyecto regression test ─────────────────────────────────

@pytest.mark.django_db
def test_hu_denominacion_de_proyecto_se_persiste_y_devuelve(
    auth_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    Regression: denominacion_de_proyecto sent in liquidacion_general is persisted
    to LiquidacionGeneral.denominacion_de_proyecto and returned in the response.

    Mirrors the Edificaciones regression test (test_denominacion_de_proyecto_se_persiste_y_devuelve).
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-DEN",
            "observacion": "Test denominacion_de_proyecto",
            "denominacion_de_proyecto": "Proyecto Residencial Los Cedros",
            "proyecto": {
                "denominacion": "Proyecto HU",
                "nombre_propietario": "Propietario Test SAC",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789015",
                    "razon_social": "Propietario Test SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["denominacion_de_proyecto"] == "Proyecto Residencial Los Cedros", \
        f"Expected denominacion_de_proyecto='Proyecto Residencial Los Cedros', got {lg.get('denominacion_de_proyecto')}"


@pytest.mark.django_db
def test_hu_denominacion_de_proyecto_null_se_devuelve_como_null(
    auth_client, municipalidad, derecho_m2_vigente, igv_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    When denominacion_de_proyecto is not provided (null), it must remain null in the response.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-DENNULL",
            "observacion": "Test denominacion_de_proyecto null",
            "denominacion_de_proyecto": None,
            "proyecto": {
                "denominacion": "Proyecto HU",
                "nombre_propietario": "Propietario Test SAC",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789016",
                    "razon_social": "Propietario Test SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100.0,
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg.get("denominacion_de_proyecto") is None, \
        f"Expected denominacion_de_proyecto=None, got {lg.get('denominacion_de_proyecto')}"
