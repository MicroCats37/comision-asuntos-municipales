"""
Integration tests for Mecánica de Suelos GET /{id} detail endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /{id} returns 200 with LiquidacionMecanicaSuelosOutput structure
- GET /{id} returns 404 when not found
- Response contains all expected nested fields

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from decimal import Decimal
import uuid

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_ms(db, tipo_mecanica_suelos):
    """Create a TarifaLiquidacionBase for Mecánica de Suelos."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_liquidacion_base_ms):
    """Create a TarifaPorMetroCuadrado for Mecánica de Suelos."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_ms,
        costo_por_m2=Decimal("150.00"),
    )


@pytest.fixture
def derecho_m2_ms(db):
    """Create a DerechoPorMetroCuadrado vigente for testing."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_ms_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_m2_ms,
    igv_vigente,
    uit_vigente,
    tarifa_m2_ms,
    tipo_mecanica_suelos,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionMecanicaSuelos + LiquidacionPorMetroCuadrado
    for testing the detail endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-MS-2024-001",
        observacion="Test liquidation MS detail",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("15000.00"),
        total=Decimal("17700.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionMecanicaSuelos (identity)
    ms = LiquidacionMecanicaSuelos.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorMetroCuadrado
    m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("100.00"),
        costo_por_m2=tarifa_m2_ms.costo_por_m2,
        derecho_minimo=derecho_m2_ms.derecho_minimo,
        derecho_maximo=derecho_m2_ms.derecho_maximo,
        tarifa_aplicada=tarifa_m2_ms,
        derecho=derecho_m2_ms,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detail_endpoint_returns_200(
    auth_client,
    liquidacion_ms_detail,
):
    """
    GET /liquidaciones/mecanica-suelos/{id} returns 200.
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_response_has_api_response_structure(
    auth_client,
    liquidacion_ms_detail,
):
    """
    Response has the ApiResponse structure: { success: bool, data: {...} }.
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200
    data = response.json()
    assert "success" in data, "Response should have 'success' key"
    assert "data" in data, "Response should have 'data' key"


@pytest.mark.django_db
def test_detail_response_has_liquidacion_ms_output_structure(
    auth_client,
    liquidacion_ms_detail,
):
    """
    Response data has the LiquidacionMecanicaSuelosOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert "liquidacion_general" in result, \
        "Response should have 'liquidacion_general'"
    assert "liquidacion_especifica" in result, \
        "Response should have 'liquidacion_especifica'"
    assert "liquidacion_tipo" in result, \
        "Response should have 'liquidacion_tipo'"


@pytest.mark.django_db
def test_detail_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_ms_detail,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200
    data = response.json()
    lg = data["data"]["liquidacion_general"]

    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert "fecha_registro" in lg
    assert "expediente" in lg
    assert "numero_revision" in lg
    assert "sub_total" in lg
    assert "total" in lg
    assert "proyecto" in lg
    assert lg["expediente"] == "EXP-MS-2024-001"


@pytest.mark.django_db
def test_detail_liquidacion_especifica_has_identity_fields(
    auth_client,
    liquidacion_ms_detail,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200
    data = response.json()
    le = data["data"]["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "area_m2" not in le, \
        "liquidacion_especifica should NOT have area_m2"


@pytest.mark.django_db
def test_detail_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_ms_detail,
):
    """
    liquidacion_tipo wrapper has calculation fields: area_m2, costo_por_m2, etc.
    """
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{liquidacion_ms_detail.id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "area_m2" in lt
    assert "costo_por_m2" in lt
    assert "derecho_minimo" in lt
    assert "tarifa_aplicada_id" in lt
    assert "derecho_aplicado_id" in lt
    assert float(lt["area_m2"]) == 100.00


@pytest.mark.django_db
def test_detail_returns_404_for_non_existent_id(
    auth_client,
    db,
):
    """
    GET /liquidaciones/mecanica-suelos/{non_existent_uuid} returns 404.
    """
    non_existent_uuid = uuid.uuid4()
    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{non_existent_uuid}")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent ID, got {response.status_code}"


@pytest.mark.django_db
def test_detail_returns_404_for_wrong_tipo_liquidacion(
    auth_client,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_habilitacion_urbana,
):
    """
    GET /liquidaciones/mecanica-suelos/{id} returns 404 when the ID belongs to
    a different tipo_liquidacion (e.g., Habilitación Urbana).
    """
    user = create_user

    # Create a HU liquidacion
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-HU-WRONG-001",
        observacion="Wrong tipo liquidacion",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("15000.00"),
        total=Decimal("17700.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    response = auth_client.get(f"/liquidaciones/mecanica-suelos/{lg.id}")

    assert response.status_code == 404, \
        f"Expected 404 for HU liquidacion accessed via MS endpoint, got {response.status_code}"
