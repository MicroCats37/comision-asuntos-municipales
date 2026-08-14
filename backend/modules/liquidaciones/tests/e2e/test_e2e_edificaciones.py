"""
E2E flow tests for Edificaciones.

Mimics the real frontend flow:
1. GET tarifas vigentes -> extract IDs and especialidades
2. POST crear liquidacion with extracted IDs (explicit mode)

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
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision as Especialidad
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel


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
def tipo_edificacion(db):
    """Get or create TipoLiquidacion for EDIFICACION."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="EDIFICACION", defaults={"nombre": "Edificaciones"})[0]


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
    """Create an Especialidad for Edificaciones testing - Civil/Estructuras."""
    return Especialidad.objects.get_or_create(
        slug="estructuras",
        defaults={"codigo": "E01", "nombre": "Estructuras"},
    )[0]


@pytest.fixture
def especialidad_sanitaria(db):
    """Create an Especialidad for Edificaciones testing - Sanitaria."""
    return Especialidad.objects.get_or_create(
        slug="sanitaria",
        defaults={"codigo": "S01", "nombre": "Sanitaria"},
    )[0]


@pytest.fixture
def especialidad_electrica(db):
    """Create an Especialidad for Edificaciones testing - Electrica."""
    return Especialidad.objects.get_or_create(
        slug="electrica",
        defaults={"codigo": "EL01", "nombre": "Electrica"},
    )[0]


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion, especialidad_estructuras):
    """Create a TarifaPorcentajeObra for Estructuras (Civil)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_estructuras,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


@pytest.fixture
def tarifa_porcentaje_obra_sanitaria(db, tarifa_liquidacion_base_edificacion, especialidad_sanitaria):
    """Create a TarifaPorcentajeObra for Sanitaria."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_sanitaria,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_electrica(db, tarifa_liquidacion_base_edificacion, especialidad_electrica):
    """Create a TarifaPorcentajeObra for Electrica."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_electrica,
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
def create_user(db):
    """Create a test user for JWT authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_e2e_edif",
        email="test_e2e_edif@example.com",
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
def test_e2e_edificaciones_flow(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_sanitaria,
    tarifa_porcentaje_obra_electrica, derecho_porcentaje_vigente,
    ubigeo_distrito
):
    """
    E2E flow for Edificaciones:

    1. GET /liquidaciones/edificaciones/tarifas/vigentes
    2. Extract list of tarifa_id and especialidad from response
    3. POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision
       with explicit tarifas array
    4. Assert 200 OK and liquidacion_tipo.detalles has same count as fetched tarifas
    """
    # Step 1: GET tarifas vigentes
    response = auth_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200, \
        f"Expected 200 from GET tarifas vigentes, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "tarifas" in result, "Result should have 'tarifas' wrapper"

    # Step 2: Extract tarifas from response
    tarifas = result["tarifas"]
    assert len(tarifas) == 3, \
        f"Expected 3 tarifas, got {len(tarifas)}"

    # Extract IDs and especialidades
    tarifa_info = []
    for tarifa in tarifas:
        tarifa_info.append({
            "id": tarifa["id"],
            "especialidad": tarifa["especialidad"],
            "porcentaje_liquidacion": tarifa["porcentaje_liquidacion"],
        })

    municipalidad_id = str(municipalidad.id)
    distrito_id = str(ubigeo_distrito.id)

    # Step 3: Construct payload using explicit mode (tarifas array)
    payload = {
        "liquidacion_general": {
            "municipalidad_id": municipalidad_id,
            "expediente": "EXP-E2E-EDIF-2024-001",
            "observacion": "E2E test Edificaciones",
            "proyecto": {
                "denominacion": "Proyecto E2E Edificaciones Test",
                "nombre_propietario": "Propietario E2E Edif SAC",
                "direccion": "Av. E2E 456, Lima",
                "distrito_id": distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Propietario E2E Edif SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": str(tarifa_info[0]["id"])},
                {"tarifa_porcentaje_obra_id": str(tarifa_info[1]["id"])},
                {"tarifa_porcentaje_obra_id": str(tarifa_info[2]["id"])},
            ],
        },
    }

    # Step 4: POST crear liquidacion
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
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
    assert lg["expediente"] == "EXP-E2E-EDIF-2024-001", \
        f"Expected expediente 'EXP-E2E-EDIF-2024-001', got {lg['expediente']}"
    assert lg["numero_revision"] == 1, \
        f"Expected numero_revision=1, got {lg['numero_revision']}"

    # Assert liquidacion_tipo.detalles has same number of items as fetched tarifas
    assert "liquidacion_tipo" in result, \
        "Result should have 'liquidacion_tipo' wrapper"
    lt = result["liquidacion_tipo"]
    assert "detalles" in lt, "liquidacion_tipo should have 'detalles'"
    assert len(lt["detalles"]) == len(tarifas), \
        f"Expected {len(tarifas)} detalles (same as fetched tarifas), got {len(lt['detalles'])}"

    # Assert liquidacion_especifica is in response
    assert "liquidacion_especifica" in result, \
        "Result should have 'liquidacion_especifica' wrapper"
    le = result["liquidacion_especifica"]
    assert "id" in le, "liquidacion_especifica should have 'id'"
    assert "numero" in le, "liquidacion_especifica should have 'numero'"

    # Verify each detalle has required fields
    for detalle in lt["detalles"]:
        assert "id" in detalle, "detalle should have 'id'"
        assert "tarifa_aplicada_id" in detalle, "detalle should have 'tarifa_aplicada_id'"
        assert "especialidad_id" in detalle, "detalle should have 'especialidad_id'"
        assert "porcentaje_aplicado" in detalle, "detalle should have 'porcentaje_aplicado'"
        assert "subtotal" in detalle, "detalle should have 'subtotal'"

    # Verify total calculation: sub_total = SUM(detalles.subtotal)
    expected_subtotal = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    actual_subtotal = Decimal(str(lg["sub_total"]))
    assert abs(expected_subtotal - actual_subtotal) < Decimal("0.01"), \
        f"Expected sub_total={expected_subtotal}, got {actual_subtotal}"
