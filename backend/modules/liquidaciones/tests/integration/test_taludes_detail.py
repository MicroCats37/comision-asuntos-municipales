"""
Integration tests for Taludes GET /{id} detail endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /{id} returns 200 with LiquidacionTaludesOutput structure
- GET /{id} returns 404 for non-existent UUID
- GET /{id} returns 404 for wrong tipo_liquidacion
- Response contains LiquidacionTaludesOutput with complete nested structure

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from decimal import Decimal
import uuid as uuid_lib

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)


# ── Detail Fixture (uses conftest fixtures) ───────────────────────────────────

@pytest.fixture
def liquidacion_taludes_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_taludes,
    especialidad_taludes,
    tipo_taludes,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionTaludes + LiquidacionPorcentajeObra
    for testing the detail endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-TALUDES-DETAIL-001",
        observacion="Test detail liquidation",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionTaludes (identity)
    taludes = LiquidacionTaludes.objects.create(
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
        tarifa_aplicada=tarifa_porcentaje_obra_taludes,
        especialidad=especialidad_taludes,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
        igv=Decimal("180.00"),
        uit=Decimal("515.00"),
        total=Decimal("1180.00"),
    )

    return lg


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detail_endpoint_returns_200(
    auth_client,
    liquidacion_taludes_detail,
):
    """
    GET /liquidaciones/taludes/{id} returns 200.
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_response_has_liquidacion_taludes_output_structure(
    auth_client,
    liquidacion_taludes_detail,
):
    """
    Response has the LiquidacionTaludesOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "liquidacion_general" in result, \
        "Detail should have 'liquidacion_general'"
    assert "liquidacion_especifica" in result, \
        "Detail should have 'liquidacion_especifica'"
    assert "liquidacion_tipo" in result, \
        "Detail should have 'liquidacion_tipo'"


@pytest.mark.django_db
def test_detail_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_taludes_detail,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

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
    assert lg["expediente"] == "EXP-TALUDES-DETAIL-001"


@pytest.mark.django_db
def test_detail_liquidacion_especifica_has_identity_fields(
    auth_client,
    liquidacion_taludes_detail,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

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
    liquidacion_taludes_detail,
):
    """
    liquidacion_tipo wrapper has calculation fields: valor_declarado, detalles, etc.
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt
    assert float(lt["valor_declarado"]) == 100000.00


@pytest.mark.django_db
def test_detail_detalles_have_required_fields(
    auth_client,
    liquidacion_taludes_detail,
):
    """
    Each detalle in liquidacion_tipo.detalles has required fields.
    """
    liquidacion_id = liquidacion_taludes_detail.id
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_id}")

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
def test_detail_returns_404_for_nonexistent_uuid(
    auth_client,
    db,
):
    """
    GET /liquidaciones/taludes/{nonexistent-uuid} returns 404.
    """
    fake_uuid = uuid_lib.uuid4()
    response = auth_client.get(f"/liquidaciones/taludes/{fake_uuid}")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent UUID, got {response.status_code}"


@pytest.mark.django_db
def test_detail_returns_404_for_wrong_tipo_liquidacion(
    auth_client,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    db,
    tipo_habilitacion_urbana,
):
    """
    GET /liquidaciones/taludes/{id} where the liquidacion is NOT of tipo TALUDES
    returns 404 (not found for this tipo).
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
    
    # Create a Habilitacion Urbana liquidacion
    user = create_user
    
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-HU-WRONG-TIPO",
        observacion="Wrong tipo liquidacion",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("500.00"),
        total=Decimal("590.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Trying to fetch HU liquidacion via Taludes endpoint returns 404
    response = auth_client.get(f"/liquidaciones/taludes/{lg.id}")

    assert response.status_code == 404, \
        f"Expected 404 for wrong tipo_liquidacion, got {response.status_code}"
