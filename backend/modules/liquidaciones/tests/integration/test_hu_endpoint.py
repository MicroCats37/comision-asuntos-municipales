"""
Integration tests for HU (Habilitación Urbana) endpoint.

Tests POST /liquidaciones/habilitacion-urbana/primera-revision endpoint.
Uses pytest-asyncio with asyncio_mode = auto (configured in pytest.ini).

Architecture: Controller -> Orchestrator -> Presenter -> HTTP Schema
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    TarifaLiquidacionBase,
)
from django.contrib.auth import get_user_model
from modules.liquidaciones.domain.constants import TipoLiquidacion

# Use Django's get_user_model to get the custom user model
User = get_user_model()


# ── Test payload builders ────────────────────────────────────────────────────


def _build_hu_payload(
    municipalidad_id: uuid.UUID,
    expediente: str = "EXP-2024-001",
    observacion: str | None = "Test observacion",
    proyecto_denominacion: str = "Proyecto Test HU",
    proyecto_propietario: str = "Propietario Test",
    area_solicitada: float = 150.0,
    tarifa_m2_id: uuid.UUID | None = None,
    include_usuario_creador: bool = False,
) -> dict:
    """
    Build a HU primera-revision payload.

    Args:
        municipalidad_id: UUID of the municipalidad
        expediente: Expediente number
        observacion: Optional observation
        proyecto_denominacion: Project name
        proyecto_propietario: Owner name
        area_solicitada: Area in m2
        tarifa_m2_id: UUID of TarifaPorMetroCuadrado (generated if None)
        include_usuario_creador: Whether to include usuario_creador in payload
    """
    if tarifa_m2_id is None:
        tarifa_m2_id = uuid.uuid4()

    payload = {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad_id),
            "expediente": expediente,
            "observacion": observacion,
            "proyecto": {
                "denominacion": proyecto_denominacion,
                "nombre_propietario": proyecto_propietario,
                "entidad_razon_social": "Entidad RUC Test",
                "entidad_tipo_documento": "RUC",
                "entidad_numero_documento": "20456789012",
                "direccion": "Av. Test 123",
                "urbanizacion": "Urb. Test",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": area_solicitada,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_m2_id),
            },
        },
    }

    if include_usuario_creador:
        payload["usuario_creador"] = str(uuid.uuid4())

    return payload


# ── Database fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def ubigeo_distrito(db):
    """Create a minimal ubigeo chain: departamento -> provincia -> distrito."""
    from modules.entidades.domain.models import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito

    dept = UbigeoDepartamento.objects.create(nombre="LIMA")
    prov = UbigeoProvincia.objects.create(nombre="LIMA", departamento=dept)
    dist = UbigeoDistrito.objects.create(nombre="MIRAFLORES", provincia=prov, ubigeo="150108")
    return dist


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    """Create a test municipalidad linked to a ubigeo distrito."""
    from modules.entidades.domain.models import Municipalidad

    muni = Municipalidad.objects.create(
        codigo="MUN001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )
    return muni


@pytest.fixture
def tarifa_m2(db):
    """Create a TarifaPorMetroCuadrado with required related objects."""
    # Create TarifaLiquidacionBase first
    tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        periodo_inicio=date(2026, 1, 1),
    )

    # Create TarifaPorMetroCuadrado
    tarifa_m2 = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base,
        costo_por_m2=Decimal("25.50"),
    )

    return tarifa_m2


@pytest.fixture
def test_user(db):
    """Create a test user for usuario_creador."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    return user


# ── Happy path test ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_happy_path(test_async_client, municipalidad, tarifa_m2, test_user):
    """
    POST the locked contract payload, expect 200 and response shape
    matches the LiquidacionHabilitacionUrbanaOutput contract.
    """
    payload = _build_hu_payload(
        municipalidad_id=municipalidad.id,
        expediente="EXP-2024-HU-001",
        observacion="Primera revision test",
        proyecto_denominacion="Edificio Residencial Los Alamos",
        proyecto_propietario="Carlos Perez Gomez",
        area_solicitada=200.0,
        tarifa_m2_id=tarifa_m2.id,
    )

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()

    # Top-level structure: ApiResponse wrapper with success=True
    assert data["success"] is True, "Expected success=True in response"
    result = data["data"]

    # Response must have exactly these 3 wrappers
    assert "liquidacion_general" in result
    assert "liquidacion_tipo" in result
    assert "liquidacion_especifica" in result

    # liquidacion_general structure
    lg = result["liquidacion_general"]
    assert "id" in lg
    assert "municipalidad_id" in lg
    assert "usuario_creador" in lg
    assert "fecha_registro" in lg
    assert "estado" in lg
    assert "expediente" in lg
    assert "observacion" in lg
    assert "retencion" in lg
    assert "numero_revision" in lg
    assert "sub_total" in lg
    assert "total" in lg
    assert "proyecto" in lg

    # Verify expediente echo back
    assert lg["expediente"] == "EXP-2024-HU-001"

    # Verify estado is PENDIENTE
    assert lg["estado"] == "PENDIENTE"

    # Verify proyecto data
    proyecto = lg["proyecto"]
    assert proyecto["denominacion"] == "Edificio Residencial Los Alamos"
    assert proyecto["nombre_propietario"] == "Carlos Perez Gomez"

    # liquidacion_tipo structure
    lt = result["liquidacion_tipo"]
    assert "id" in lt
    assert "numero" in lt

    # liquidacion_especifica structure
    le = result["liquidacion_especifica"]
    assert "datos" in le
    assert "tarifa" in le

    datos = le["datos"]
    assert "area_m2" in datos
    assert "costo_por_m2" in datos
    assert "minimo" in datos

    tarifa = le["tarifa"]
    assert "tarifa_m2_id" in tarifa


# ── Validation tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_area_zero_returns_400(test_async_client, municipalidad, tarifa_m2):
    """
    area_solicitada = 0 should return 400.

    Validation happens in orchestrator: area_solicitada must be > 0.
    """
    payload = _build_hu_payload(
        municipalidad_id=municipalidad.id,
        area_solicitada=0,
        tarifa_m2_id=tarifa_m2.id,
    )

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for area=0, got {response.status_code}: {response.json()}"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_area_negative_returns_400(test_async_client, municipalidad, tarifa_m2):
    """
    area_solicitada = -1 should return 400.

    Validation happens in orchestrator: area_solicitada must be > 0.
    """
    payload = _build_hu_payload(
        municipalidad_id=municipalidad.id,
        area_solicitada=-1,
        tarifa_m2_id=tarifa_m2.id,
    )

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, f"Expected 400 for area=-1, got {response.status_code}: {response.json()}"


# ── Response shape tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_response_has_3_wrappers(test_async_client, municipalidad, tarifa_m2):
    """
    Assert response has exactly liquidacion_general, liquidacion_tipo, liquidacion_especifica.

    No additional top-level keys should be present.
    """
    payload = _build_hu_payload(
        municipalidad_id=municipalidad.id,
        area_solicitada=100.0,
        tarifa_m2_id=tarifa_m2.id,
    )

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()["data"]

    # Exactly 3 wrappers, no more
    assert set(data.keys()) == {"liquidacion_general", "liquidacion_tipo", "liquidacion_especifica"}


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_no_snapshot_in_output(test_async_client, municipalidad, tarifa_m2):
    """
    Assert igv_snapshot, uit_snapshot, tipo_calculo, concepto are NOT in the response.

    These fields are internal to the model but NOT part of the output contract.
    This test ensures the presenter correctly filters them out.
    """
    payload = _build_hu_payload(
        municipalidad_id=municipalidad.id,
        area_solicitada=100.0,
        tarifa_m2_id=tarifa_m2.id,
    )

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    assert response.status_code == 200
    result = response.json()["data"]

    # Build flattened list of all keys in response
    def flatten_keys(obj, prefix=""):
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(f"{prefix}{k}")
                keys.update(flatten_keys(v, f"{prefix}{k}."))
        return keys

    all_keys = flatten_keys(result)

    # These internal model fields must not appear in output
    forbidden = {"igv_snapshot", "uit_snapshot", "tipo_calculo", "concepto"}
    found_forbidden = forbidden.intersection(all_keys)
    assert not found_forbidden, (
        f"Found forbidden internal fields in response: {found_forbidden}. "
        f"Output should not expose model snapshot fields."
    )


# ── Input validation tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_hu_primera_revision_no_usuario_creador_in_input(test_async_client, municipalidad, tarifa_m2):
    """
    Test the endpoint with a payload that has NO usuario_creador.

    The orchestrator/controller should NOT raise an error - usuario_creador
    is NOT part of the input contract and is set by the system.
    """
    # Build payload WITHOUT usuario_creador
    payload = {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-2024-NO-USER",
            "observacion": "Test without usuario_creador",
            "proyecto": {
                "denominacion": "Proyecto Sin Usuario",
                "nombre_propietario": "Propietario Test",
                "entidad_razon_social": "Entidad RUC",
                "entidad_tipo_documento": "RUC",
                "entidad_numero_documento": "20456789099",
                "direccion": "Av. Sin Usuario 123",
                "urbanizacion": "Urb. Sin",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": 150.0,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_m2.id),
            },
        },
    }

    # Ensure usuario_creador is NOT in payload
    assert "usuario_creador" not in payload

    response = await test_async_client.post(
        "/api/liquidaciones/habilitacion-urbana/primera-revision",
        json=payload,
    )

    # Should succeed - the endpoint doesn't require usuario_creador in input
    assert response.status_code == 200, (
        f"Expected 200 when usuario_creador is absent, "
        f"got {response.status_code}: {response.json()}"
    )

    data = response.json()
    assert data["success"] is True
    # usuario_creador in output should be present but with null id since no user was set
    usuario_creador_id = data["data"]["liquidacion_general"]["usuario_creador"]["id"]
    # The id can be None since no user was associated (or a system user id)
    assert usuario_creador_id is None or isinstance(usuario_creador_id, str)
