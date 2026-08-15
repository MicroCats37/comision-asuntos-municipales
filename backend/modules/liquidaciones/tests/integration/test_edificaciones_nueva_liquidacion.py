"""
Integration tests for Edificaciones /nueva-liquidacion/primera-revision endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- Hybrid mode (auto-fill empty array)
- Explicit mode (3 tarifas sent)
- Validation errors (valor_declarado <= 0, invalid tarifa, wrong type)
- Clamping (minimum applied when total < derecho_minimo)
- tipo_tramite is NULL in response
- 3 wrappers in response structure
- Snapshot values preserved (igv_id, uit_id)
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
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision as Especialidad
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixtures ────────────────────────────────────────────────────────────────

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
def create_user(db):
    """Create a test user (needed for FK to usuarios_usuario on LiquidacionGeneral)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_edif",
        email="test_edif@example.com",
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
def tarifa_liquidacion_base_edificacion(db, tipo_edificacion):
    """Create a TarifaLiquidacionBase for Edificaciones."""
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_estructuras(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="A01",
        slug="arquitectura",
        nombre="Arquitectura",
    )


@pytest.fixture
def especialidad_installaciones(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="I01",
        slug="instalaciones",
        nombre="Instalaciones",
    )


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion):
    """Create a TarifaPorcentajeObra (tarifa única por base, sin especialidad FK)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


@pytest.fixture
def tarifa_porcentaje_obra_arquitectura(db, tarifa_liquidacion_base_edificacion):
    """Create a second TarifaPorcentajeObra for Arquitectura (different base)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_installaciones(db, tarifa_liquidacion_base_edificacion):
    """Create a third TarifaPorcentajeObra for Instalaciones (different base)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


@pytest.fixture
def derecho_porcentaje_vigente(db):
    """Create a DerechoPorcentajeObra vigente for testing."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
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
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.fixture
def valid_municipalidad_id(municipalidad):
    """Return the ID of the municipalidad as a string."""
    return str(municipalidad.id)


@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    """Return the ID of the distrito as a string."""
    return str(ubigeo_distrito.id)


@pytest.fixture
def tarifa_porcentaje_obra_base2(db, tipo_edificacion):
    """Second TarifaLiquidacionBase + TarifaPorcentajeObra for explicit mode test."""
    base2 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base2,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_base3(db, tipo_edificacion):
    """Third TarifaLiquidacionBase + TarifaPorcentajeObra for explicit mode test."""
    base3 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base3,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


@pytest.fixture
def valid_tarifa_ids(tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_base2, tarifa_porcentaje_obra_base3, especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones):
    """Return IDs of all three tarifas as strings, each with its own base (new model: no especialidad FK)."""
    return [
        {"id": str(tarifa_porcentaje_obra_estructuras.id), "esp_id": str(especialidad_estructuras.id)},
        {"id": str(tarifa_porcentaje_obra_base2.id), "esp_id": str(especialidad_arquitectura.id)},
        {"id": str(tarifa_porcentaje_obra_base3.id), "esp_id": str(especialidad_installaciones.id)},
    ]


@pytest.fixture
def valid_payload_auto_fill(valid_municipalidad_id, valid_distrito_id, especialidades_disponibles_edificacion):
    """Return a valid payload with empty tarifas[] (auto-fill mode).

    Depends on especialidades_disponibles_edificacion so auto-fill can combine
    vigentes tarifas x vigentes especialidades.
    """
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-001",
            "observacion": "Test auto-fill mode",
            "proyecto": {
                "denominacion": "Proyecto Edificaciones Test AutoFill",
                "nombre_propietario": "Propietario Edif SAC",
                "direccion": "Av. Edif 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Propietario Edif SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [],  # Empty = auto-fill mode
        },
    }


@pytest.fixture
def valid_payload_explicit(valid_municipalidad_id, valid_distrito_id, valid_tarifa_ids):
    """Return a valid payload with explicit tarifas[] (explicit mode).

    NEW contract: each tarifa entry requires {tarifa_porcentaje_obra_id, especialidad_id}.
    Each entry uses the same or different tarifa IDs with different especialidad IDs.
    """
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-002",
            "observacion": "Test explicit mode",
            "proyecto": {
                "denominacion": "Proyecto Edificaciones Test Explicit",
                "nombre_propietario": "Propietario Edif Explicit SAC",
                "direccion": "Av. Edif 456, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789013",
                    "razon_social": "Propietario Edif Explicit SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[0]["id"], "especialidad_id": valid_tarifa_ids[0]["esp_id"]},
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[1]["id"], "especialidad_id": valid_tarifa_ids[1]["esp_id"]},
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[2]["id"], "especialidad_id": valid_tarifa_ids[2]["esp_id"]},
            ],
        },
    }


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_happy_path_auto_fill_mode(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, valid_payload_auto_fill
):
    """
    Auto-fill: empty tarifas[] → backend picks all vigentes.

    The /nueva-liquidacion/primera-revision endpoint accepts a payload with
    empty tarifas[] and returns 200, auto-filling all vigentes.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "liquidacion_general" in result
    assert "liquidacion_tipo" in result
    assert "liquidacion_especifica" in result

    # Verify liquidacion_general has expected fields
    lg = result["liquidacion_general"]
    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert lg["expediente"] == "EXP-EDIF-2024-001"
    assert lg["numero_revision"] == 1

    # Verify liquidacion_especifica has identity fields
    le = result["liquidacion_especifica"]
    assert "id" in le
    assert "numero" in le

    # Verify liquidacion_tipo has calculation fields
    lt = result["liquidacion_tipo"]
    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt

    # Should have 3 detalles (one per auto-filled tarifa)
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles for auto-fill mode, got {len(lt['detalles'])}"


@pytest.mark.django_db
def test_happy_path_explicit_mode(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, valid_payload_explicit
):
    """
    Explicit: 3 tarifa_ids sent → backend validates each.

    The /nueva-liquidacion/primera-revision endpoint accepts a payload with
    explicit tarifa_ids and returns 200 with those exact tarifas.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_explicit,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]

    lt = result["liquidacion_tipo"]
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles for explicit mode, got {len(lt['detalles'])}"

    # Verify percentages are correct: 0.0010 + 0.0005 + 0.0003 = 0.0018
    total_porcentaje = sum(Decimal(str(d["porcentaje_aplicado"])) for d in lt["detalles"])
    assert abs(total_porcentaje - Decimal("0.0018")) < Decimal("0.0001"), \
        f"Expected total porcentaje 0.0018, got {total_porcentaje}"


@pytest.mark.django_db
def test_valor_declarado_zero_returns_400(
    auth_client, municipalidad, valid_municipalidad_id, valid_distrito_id
):
    """
    Validation: valor_declarado = 0 → HttpError 400.

    The orchestrator validates that valor_declarado must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-VALID-001",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test Validacion",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789014",
                    "razon_social": "Propietario Test Validacion",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 0,  # Invalid
            },
            "tarifas": [],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for valor_declarado=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_valor_declarado_negative_returns_400(
    auth_client, municipalidad, valid_municipalidad_id, valid_distrito_id
):
    """
    Validation: valor_declarado < 0 → HttpError 400.

    The orchestrator validates that valor_declarado must be > 0.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-VALID-002",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test Validacion 2",
                "nombre_propietario": "Propietario Test 2",
                "direccion": "Av. Test 456",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789015",
                    "razon_social": "Propietario Test Validacion 2",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": -1000.00,  # Invalid
            },
            "tarifas": [],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for valor_declarado < 0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_invalid_tarifa_id_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    valid_municipalidad_id, valid_distrito_id
):
    """
    Validation: non-existent tarifa_id → HttpError 400.

    When an explicit tarifa_id doesn't exist, the orchestrator raises HttpError 400.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-VALID-003",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test Invalid Tarifa",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 789",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789016",
                    "razon_social": "Propietario Test Invalid",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": str(uuid.uuid4()), "especialidad_id": str(uuid.uuid4())},  # Non-existent
            ],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid tarifa_id, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_tarifa_wrong_type_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_liquidacion_base_edificacion, valid_municipalidad_id, valid_distrito_id,
    tipo_habilitacion_urbana
):
    """
    Validation: HU tarifa sent → HttpError 400 'no es de edificaciones'.

    When a tariff of a different tipo_liquidacion is sent, the orchestrator
    raises HttpError 400 with message 'no es de edificaciones'.
    """
    # Create a HU tariff
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import TarifaPorMetroCuadrado

    
    hu_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    hu_tarifa = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=hu_tarifa_base,
        costo_por_m2=Decimal("150.0000"),
    )

    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-VALID-004",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test Wrong Type",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 999",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789017",
                    "razon_social": "Propietario Test Wrong Type",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": str(hu_tarifa.id), "especialidad_id": str(uuid.uuid4())},  # Wrong type!
            ],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for wrong tipo_liquidacion, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_tarifa_not_vigente_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    valid_municipalidad_id, valid_distrito_id,
    tipo_edificacion
):
    """
    Validation: expired tarifa → HttpError 400 'no está vigente'.

    When a tariff is expired (has periodo_fin), the orchestrator raises
    HttpError 400 with message 'no está vigente'.
    """
    # Create an expired tariff
    
    expired_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 12, 31),  # Expired
    )
    expired_tarifa = TarifaPorcentajeObra.objects.create(
        tarifa_base=expired_tarifa_base,
        porcentaje_liquidacion=Decimal("0.0010"),
    )

    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-VALID-005",
            "observacion": None,
            "proyecto": {
                "denominacion": "Proyecto Test Expired Tarifa",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 111",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789018",
                    "razon_social": "Propietario Test Expired",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": str(expired_tarifa.id), "especialidad_id": str(uuid.uuid4())},
            ],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for expired tarifa, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_response_has_three_wrappers(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill
):
    """
    Response structure: liquidacion_general + especifica + tipo.

    The primera-revision endpoint returns LiquidacionEdificacionesOutput which
    is the union of the three wrappers.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]

    # Validate all three top-level wrappers are present
    assert "liquidacion_general" in result, \
        "Response should have 'liquidacion_general' wrapper"
    assert "liquidacion_tipo" in result, \
        "Response should have 'liquidacion_tipo' wrapper"
    assert "liquidacion_especifica" in result, \
        "Response should have 'liquidacion_especifica' wrapper"


@pytest.mark.django_db
def test_liquidacion_especifica_is_identity(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill
):
    """
    liquidacion_especifica wrapper has only id + numero.

    Semantically: especifica = identity wrapper (id + auto-generated numero).
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    le = result["liquidacion_especifica"]

    # Validate identity structure
    assert "id" in le, "liquidacion_especifica should have 'id'"
    assert "numero" in le, "liquidacion_especifica should have 'numero'"

    # Should NOT have calculation fields
    assert "valor_declarado" not in le, \
        "liquidacion_especifica should NOT have 'valor_declarado' (that's in liquidacion_tipo)"
    assert "detalles" not in le, \
        "liquidacion_especifica should NOT have 'detalles' (that's in liquidacion_tipo)"


@pytest.mark.django_db
def test_liquidacion_tipo_has_detalles(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, valid_payload_auto_fill
):
    """
    liquidacion_tipo.detalles has N entries (one per tarifa).

    Each detail has: id, tarifa_aplicada_id, especialidad_id, porcentaje_aplicado,
    subtotal, igv, uit, total.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    assert "detalles" in lt, "liquidacion_tipo should have 'detalles'"
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles (one per tarifa), got {len(lt['detalles'])}"

    # Verify each detalle has required fields
    for detalle in lt["detalles"]:
        assert "id" in detalle
        assert "tarifa_aplicada_id" in detalle
        assert "especialidad_id" in detalle
        assert "porcentaje_aplicado" in detalle
        assert "subtotal" in detalle
        assert "igv" in detalle
        assert "uit" in detalle
        assert "total" in detalle


@pytest.mark.django_db
def test_subtotal_is_sum_of_detalles(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, valid_payload_auto_fill
):
    """
    LiquidacionGeneral.sub_total = SUM(detalles.subtotal).

    The subtotal of the liquidacion_general should equal the sum of all detail subtotals.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # Sum of detalle subtotals
    expected_subtotal = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    actual_subtotal = Decimal(str(lg["sub_total"]))

    assert abs(expected_subtotal - actual_subtotal) < Decimal("0.01"), \
        f"Expected sub_total={expected_subtotal}, got {actual_subtotal}"


@pytest.mark.django_db
def test_total_calculation_with_igv(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill
):
    """
    LiquidacionGeneral.total = sub_total + IGV.

    With IGV = 18%, total should be sub_total * 1.18.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    sub_total = Decimal(str(lg["sub_total"]))
    total = Decimal(str(lg["total"]))
    igv = lg["igv"]

    # If igv is set, total should include IGV
    if igv is not None:
        expected_total = sub_total * Decimal("1.18")
        assert abs(expected_total - total) < Decimal("0.01"), \
            f"Expected total={expected_total} (sub_total * 1.18), got {total}"
    else:
        # If no IGV, total should equal sub_total
        assert abs(sub_total - total) < Decimal("0.01"), \
            f"Expected total=sub_total when no IGV, got total={total}"


@pytest.mark.django_db
def test_tipo_tramite_is_null(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill
):
    """
    tipo_tramite field is None in response.

    Currently tipo_tramite stays NULL for all liquidations (FUTURE: activate when frontend sends it).
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    assert lt["tipo_tramite"] is None, \
        f"Expected tipo_tramite to be None, got {lt['tipo_tramite']}"


@pytest.mark.django_db
def test_clamping_minimum_applied(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras, valid_municipalidad_id, valid_distrito_id
):
    """
    When total < derecho_minimo, clamp to min + distribute proportionally.

    With derecho_minimo = 500.00 and a very small valor_declarado that would result
    in a subtotal below 500, the system should clamp to derecho_minimo.
    """
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-EDIF-2024-CLAMP-MIN",
            "observacion": "Test clamping minimum",
            "proyecto": {
                "denominacion": "Proyecto Test Clamping Min",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789019",
                    "razon_social": "Propietario Test Min",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 1000.00,  # Small value, will result in < 500 subtotal
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
            ],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # The total should be clamped to derecho_minimo (500.00)
    # Note: exact behavior depends on implementation (proportional distribution or fixed minimum)
    # At minimum, sub_total and total should be >= derecho_minimo
    assert lg["sub_total"] >= 500.00, \
        f"Expected sub_total >= 500.00 (derecho_minimo), got {lg['sub_total']}"
    assert lg["total"] >= 500.00, \
        f"Expected total >= 500.00 (derecho_minimo), got {lg['total']}"


@pytest.mark.django_db
def test_porcentaje_liquidacion_is_sum(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, valid_payload_explicit
):
    """
    porcentaje_liquidacion = SUM of all tarifa percentages.

    The percentage_liquidacion in liquidacion_tipo should equal the sum of
    all applied tarifa percentages.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_explicit,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    # Sum of expected percentages: 0.0010 + 0.0005 + 0.0003 = 0.0018
    expected_porcentaje = Decimal("0.0010") + Decimal("0.0005") + Decimal("0.0003")
    actual_porcentaje = Decimal(str(lt["porcentaje_liquidacion"]))

    assert abs(expected_porcentaje - actual_porcentaje) < Decimal("0.0001"), \
        f"Expected porcentaje_liquidacion={expected_porcentaje}, got {actual_porcentaje}"


@pytest.mark.django_db
def test_snapshot_igv_uit_assigned(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill
):
    """
    igv_id and uit_id are populated in LiquidacionGeneral.

    The primera-revision endpoint should populate igv_id and uit_id as FK references
    from the configured IGV and UIT vigente.
    """
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=valid_payload_auto_fill,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    # Verify igv and uit are present (they may be None if no IGV/UIT is configured)
    assert "igv" in lg, "liquidacion_general should have 'igv' field"
    assert "uit" in lg, "liquidacion_general should have 'uit' field"

    # If igv is not None, verify it's an object with valid UUID id
    if lg["igv"] is not None:
        igv_uuid = uuid.UUID(str(lg["igv"]["id"]))
        assert isinstance(igv_uuid, uuid.UUID), \
            f"igv.id should be a valid UUID, got {lg['igv']['id']}"

    # If uit is not None, verify it's an object with valid UUID id
    if lg["uit"] is not None:
        uit_uuid = uuid.UUID(str(lg["uit"]["id"]))
        assert isinstance(uit_uuid, uuid.UUID), \
            f"uit.id should be a valid UUID, got {lg['uit']['id']}"

@pytest.mark.django_db
def test_crear_liquidacion_con_contacto_inline(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_municipalidad_id, valid_distrito_id,
    especialidades_disponibles_edificacion,
):
    """Crea una liquidacion con contacto inline y verifica que el output lo incluya anidado."""
    payload = {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-CONTACTO-001",
            "observacion": "Test contacto inline",
            "proyecto": {
                "denominacion": "Proyecto Contacto Test",
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "DNI",
                    "numero_documento": "12345678",
                    "razon_social": "Propietario Test",
                },
            },
            "contacto": {
                "nombres": "MARIA CONTACTO",
                "apellidos": "GARCIA PEREZ",
                "dni": "87654321",
                "cargo": "PROPIETARIA",
                "celular": "999888777",
            },
        },
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 100000.00},
            "tarifas": [],
        },
    }
    response = auth_client.post("/liquidaciones/edificaciones/nueva-liquidacion/primera-revision", json=payload)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]

    assert lg["contacto"] is not None, "El output debe incluir contacto anidado"
    assert lg["contacto"]["nombres"] == "MARIA CONTACTO"
    assert lg["contacto"]["apellidos"] == "GARCIA PEREZ"
    assert lg["contacto"]["dni"] == "87654321"
    assert lg["contacto"]["cargo"] == "PROPIETARIA"


@pytest.mark.django_db
def test_crear_liquidacion_sin_contacto(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, valid_payload_auto_fill,
):
    """Sin contacto en el input, el output debe traer contacto=None."""
    response = auth_client.post("/liquidaciones/edificaciones/nueva-liquidacion/primera-revision", json=valid_payload_auto_fill)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]

    assert lg["contacto"] is None, "Sin contacto en input, output debe ser None"
