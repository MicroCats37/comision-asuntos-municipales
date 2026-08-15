"""
Integration tests for Impacto Vial GET /{id} detail endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /liquidaciones/impacto-vial/{liquidacion_id} returns 200 with LiquidacionImpactoVialOutput structure
- GET /liquidaciones/impacto-vial/{liquidacion_id} returns 404 for non-existent ID
- Response matches the expected output schema

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
import uuid
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)


# ── Fixture (uses conftest fixtures) ─────────────────────────────────────────

@pytest.fixture
def liquidacion_iv_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_iv,
    especialidad_impacto_vial,
    tipo_impacto_vial,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionImpactoVial + LiquidacionPorcentajeObra
    for testing the detail endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IV-DETAIL-001",
        observacion="Test liquidation for IV detail",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_impacto_vial,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionImpactoVial (identity)
    iv = LiquidacionImpactoVial.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorcentajeObra
    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite=None,
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    # Create LiquidacionPorcentajeObraDetalle
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_iv,
        especialidad=especialidad_impacto_vial,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
        igv=Decimal("180.00"),
        uit=Decimal("515.00"),
        total=Decimal("1180.00"),
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detail_endpoint_returns_200(
    auth_client,
    liquidacion_iv_detail,
):
    """
    GET /liquidaciones/impacto-vial/{liquidacion_id} returns 200 for valid ID.
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_response_has_liquidacion_impacto_vial_output_structure(
    auth_client,
    liquidacion_iv_detail,
):
    """
    Response has the LiquidacionImpactoVialOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Top-level structure
    assert "liquidacion_general" in result, \
        "Response should have 'liquidacion_general'"
    assert "liquidacion_especifica" in result, \
        "Response should have 'liquidacion_especifica'"
    assert "liquidacion_tipo" in result, \
        "Response should have 'liquidacion_tipo'"


@pytest.mark.django_db
def test_detail_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_iv_detail,
):
    """
    liquidacion_general wrapper has all expected fields.
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

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


@pytest.mark.django_db
def test_detail_liquidacion_especifica_has_identity_fields(
    auth_client,
    liquidacion_iv_detail,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    Should NOT have valor_declarado (that's in liquidacion_tipo).
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    le = data["data"]["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "valor_declarado" not in le, \
        "liquidacion_especifica should NOT have valor_declarado"


@pytest.mark.django_db
def test_detail_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_iv_detail,
):
    """
    liquidacion_tipo wrapper has calculation fields: valor_declarado, detalles, etc.
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "derecho_minimo" in lt
    assert "derecho_maximo" in lt
    assert "detalles" in lt


@pytest.mark.django_db
def test_detail_detalles_have_required_fields(
    auth_client,
    liquidacion_iv_detail,
):
    """
    Each detalle in liquidacion_tipo.detalles has required fields.
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert len(lt["detalles"]) >= 1, "Should have at least 1 detalle"

    detalle = lt["detalles"][0]
    assert "id" in detalle
    assert "tarifa_aplicada_id" in detalle
    assert "especialidad_id" in detalle
    assert "porcentaje_aplicado" in detalle
    assert "subtotal" in detalle
    assert "igv" in detalle
    assert "uit" in detalle
    assert "total" in detalle


@pytest.mark.django_db
def test_detail_endpoint_returns_404_for_invalid_id(
    auth_client,
    db,
):
    """
    GET /liquidaciones/impacto-vial/{non_existent_id} returns 404.
    Uses a valid UUID format that doesn't exist in the database.
    """
    non_existent_id = uuid.uuid4()
    response = auth_client.get(f"/liquidaciones/impacto-vial/{non_existent_id}")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent ID, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_endpoint_returns_404_for_wrong_type_liquidacion(
    auth_client,
    db,
    municipalidad,
    proyecto,
    create_user,
    tipo_habilitacion_urbana,
):
    """
    GET /liquidaciones/impacto-vial/{id_of_different_type} returns 404.
    This creates a liquidacion of a different type (Habilitacion Urbana) and
    verifies that requesting it via the IV endpoint returns 404.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
    
    user = create_user
    

    # Create HU liquidacion
    hu_lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-HU-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("500.00"),
        total=Decimal("590.00"),
    )

    # Try to fetch it via IV endpoint - should return 404
    response = auth_client.get(f"/liquidaciones/impacto-vial/{hu_lg.id}")

    assert response.status_code == 404, \
        f"Expected 404 when fetching HU liquidacion via IV endpoint, got {response.status_code}"


@pytest.mark.django_db
def test_detail_id_matches_output_liquidacion_general_id(
    auth_client,
    liquidacion_iv_detail,
):
    """
    The id in liquidacion_general matches the requested liquidacion_id.
    """
    liquidacion_id = liquidacion_iv_detail.id
    response = auth_client.get(f"/liquidaciones/impacto-vial/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lg_id_in_response = data["data"]["liquidacion_general"]["id"]

    # The ID returned should match the requested ID
    assert str(lg_id_in_response) == str(liquidacion_id)
