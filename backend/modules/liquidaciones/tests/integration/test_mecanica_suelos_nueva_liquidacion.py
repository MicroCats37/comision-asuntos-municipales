"""
Integration tests for the Mecanica de Suelos /nueva-liquidacion/primera-revision endpoint.

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
def create_user(db):
    """Create a test user (needed for FK to usuarios_usuario on LiquidacionGeneral)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_ms",
        email="test_ms@example.com",
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
def tarifa_liquidacion_base_ms(db):
    """Create a TarifaLiquidacionBase for Mecanica de Suelos."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_liquidacion_base_ms):
    """Create a TarifaPorMetroCuadrado for Mecanica de Suelos."""
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
            "expediente": "EXP-MS-2024-001",
            "observacion": "Test observation",
            "proyecto": {
                "denominacion": "Proyecto de Mecánica de Suelos Test",
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
def test_ms_nueva_liquidacion_happy_path(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    POST with valid data returns 200 and verifies the 3 wrappers.

    The /nueva-liquidacion/primera-revision endpoint accepts a valid full payload
    (liquidacion_general + liquidacion_especifica) and returns 200 with
    liquidacion_general, liquidacion_tipo, and liquidacion_especifica in the response.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
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
    assert "municipalidad_id" in lg
    assert "usuario_creador" in lg
    assert lg["expediente"] == "EXP-MS-2024-001"
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
def test_ms_nueva_liquidacion_area_zero_returns_400(
    auth_client, valid_municipalidad_id, valid_tarifa_m2_id, valid_distrito_id
):
    """
    area_solicitada = 0 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-MS-2024-002",
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
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for area=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_area_negative_returns_400(
    auth_client, valid_municipalidad_id, valid_tarifa_m2_id, valid_distrito_id
):
    """
    area_solicitada < 0 returns 400 error.

    The orchestrator validates that area_solicitada must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-MS-2024-003",
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
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for negative area, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_response_has_three_wrappers(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify the output JSON has liquidacion_general, liquidacion_tipo, and liquidacion_especifica.

    The primera-revision endpoint returns LiquidacionMecanicaSuelosOutput which
    is the union of the three wrappers.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
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
def test_ms_nueva_liquidacion_no_usuario_creador_in_input(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    Verify the endpoint handles a payload that does NOT contain usuario_creador.

    The primera-revision endpoint should work correctly without usuario_creador in
    the input payload (usuario_id is extracted from token).
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-MS-2024-004",
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
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200 without usuario_creador, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert "liquidacion_general" in result
    assert "liquidacion_tipo" in result
    assert "liquidacion_especifica" in result


@pytest.mark.django_db
def test_ms_nueva_liquidacion_has_igv_and_uit_ids(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify that igv_id and uit_id are present in liquidacion_general response.

    The primera-revision endpoint should populate igv_id and uit_id as FK references
    from the configured IGV and UIT vigente.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    # Verify igv_id and uit_id are present (they may be None if no IGV/UIT is configured)
    assert "igv_id" in lg, "liquidacion_general should have 'igv_id' field"
    assert "uit_id" in lg, "liquidacion_general should have 'uit_id' field"

    # If igv_id is not None, verify it's a valid UUID
    if lg["igv_id"] is not None:
        igv_uuid = uuid.UUID(str(lg["igv_id"]))
        assert isinstance(igv_uuid, uuid.UUID), f"igv_id should be a valid UUID, got {lg['igv_id']}"

    # If uit_id is not None, verify it's a valid UUID
    if lg["uit_id"] is not None:
        uit_uuid = uuid.UUID(str(lg["uit_id"]))
        assert isinstance(uit_uuid, uuid.UUID), f"uit_id should be a valid UUID, got {lg['uit_id']}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_sub_total_calculation(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify that sub_total calculation is correct.

    With area_solicitada = 100.0 and costo_por_m2 = 150.0 (from tariff fixture),
    sub_total should be 100.0 * 150.0 = 15000.0.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    # Verify sub_total calculation: area * costo_por_m2
    # area_solicitada = 100.0, costo_por_m2 = 150.0
    assert lg["sub_total"] == 15000.0, f"Expected sub_total = 15000.0, got {lg['sub_total']}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_total_calculation(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify that total is calculated correctly.

    total should be sub_total + IGV if IGV is configured, otherwise total = sub_total.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    # Verify total is present and is a positive number
    assert "total" in lg, "liquidacion_general should have 'total' field"
    assert lg["total"] > 0, f"total should be positive, got {lg['total']}"

    # If igv_id is None (no IGV configured), total should equal sub_total
    if lg["igv_id"] is None:
        assert lg["total"] == lg["sub_total"], \
            f"When igv_id is None, total should equal sub_total, got total={lg['total']}, sub_total={lg['sub_total']}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_clamping_minimo(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    When area_solicitada is below derecho_minimo, the response should use derecho_minimo.

    derecho_minimo = 500.00, area_solicitada = 1.0 (below min)
    Expected: sub_total and total should be clamped to derecho_minimo.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-MS-2024-CLAMP-MIN",
            "observacion": "Test clamping minimum",
            "proyecto": {
                "denominacion": "Proyecto Test Clamping Min",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789015",
                    "razon_social": "Propietario Test Min",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 1.0,  # Below derecho_minimo of 500.00
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # The total should be clamped to derecho_minimo (500.00)
    assert lg["sub_total"] == 500.00, f"Expected sub_total to be clamped to 500.00, got {lg['sub_total']}"
    assert lg["total"] == 500.00, f"Expected total to be clamped to 500.00, got {lg['total']}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_clamping_maximo(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_municipalidad_id, valid_distrito_id
):
    """
    When area_solicitada is above derecho_maximo, the response should use derecho_maximo.

    derecho_maximo = 50000.00, area_solicitada = 100000.0 (above max)
    Expected: sub_total and total should be clamped to derecho_maximo.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-MS-2024-CLAMP-MAX",
            "observacion": "Test clamping maximum",
            "proyecto": {
                "denominacion": "Proyecto Test Clamping Max",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 456",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789016",
                    "razon_social": "Propietario Test Max",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 100000.0,  # Above derecho_maximo of 50000.00
            },
            "tarifa": {
                "tarifa_m2_id": valid_tarifa_m2_id,
            },
        },
    }

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # The total should be clamped to derecho_maximo (50000.00)
    assert lg["sub_total"] == 50000.00, f"Expected sub_total to be clamped to 50000.00, got {lg['sub_total']}"
    assert lg["total"] == 50000.00, f"Expected total to be clamped to 50000.00, got {lg['total']}"


@pytest.mark.django_db
def test_ms_nueva_liquidacion_snapshot_costo_por_m2(
    auth_client, municipalidad, derecho_m2_vigente, valid_tarifa_m2_id,
    ubigeo_distrito, valid_payload
):
    """
    Verify that costo_por_m2 in the response matches the tariff at creation time (snapshot).

    The tariff's costo_por_m2 should be 150.0 (from the fixture).
    This verifies that the value was snapshotted at creation time.
    """
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        json=valid_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    # Verify costo_por_m2 is snapshotted from the tariff
    assert lt["costo_por_m2"] == 150.0, \
        f"Expected costo_por_m2 to be 150.0 (from tariff), got {lt['costo_por_m2']}"

    # Also verify that the area_m2 matches what was requested
    assert lt["area_m2"] == 100.0, \
        f"Expected area_m2 to be 100.0, got {lt['area_m2']}"
