"""
Integration tests for general detail endpoint GET /liquidaciones/generales/{id}/detalle.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /liquidaciones/generales/{id}/detalle returns 200 with polymorphic structure
- Response contains liquidacion_general, liquidacion_especifica, liquidacion_tipo
- Returns 404 for non-existent ID
- Polymorphic dispatch: same endpoint returns correct type-specific structure for different tipos

Fixtures are shared via conftest.py.
"""
import pytest
import uuid
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorMetroCuadrado as LiquidacionM2,
)


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_edificacion_for_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionEdificacion + LiquidacionPorcentajeObra
    for testing the general detail endpoint (EDIFICACION type).
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-GEN-DETAIL-EDIF-001",
        observacion="Test liquidation for general detail endpoint",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    edif = LiquidacionEdificacion.objects.create(
        liquidacion=lg,
        numero=1,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


@pytest.fixture
def liquidacion_hu_for_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_habilitacion_urbana,
    tarifa_m2_hu,
    derecho_m2_vigente,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionHabilitacionUrbana + LiquidacionM2
    for testing the general detail endpoint (HABILITACION_URBANA type).
    """
    from modules.entidades.domain.models import Entidad

    user = create_user

    # Clone proyecto to avoid UNIQUE constraint with previous test's proyecto
    entidad = Entidad.objects.create(
        tipo_documento="DNI",
        numero_documento="11223344",
    )
    from modules.liquidaciones.domain.models.proyecto import Proyecto
    from modules.entidades.domain.models import UbigeoDistrito

    cloned_proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario HU Test",
        direccion="Av. HU 456",
        distrito_id=proyecto.distrito_id,
        entidad_tipo_documento="DNI",
        entidad_numero_documento="11223344",
        entidad_razon_social="Propietario HU Test",
    )

    lg = LiquidacionGeneral.objects.create(
        proyecto=cloned_proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-GEN-DETAIL-HU-001",
        observacion="Test liquidation HU for general detail endpoint",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("500.00"),
        total=Decimal("590.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionHabilitacionUrbana.objects.create(
        liquidacion=lg,
        numero=1,
    )

    LiquidacionM2.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("150.00"),
        costo_por_m2=tarifa_m2_hu.costo_por_m2,
        derecho_minimo=derecho_m2_vigente.derecho_minimo,
        derecho_maximo=derecho_m2_vigente.derecho_maximo,
        tarifa_aplicada=tarifa_m2_hu,
        derecho=derecho_m2_vigente,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_general_detail_endpoint_returns_200_for_valid_id(
    auth_client,
    liquidacion_edificacion_for_detail,
):
    """
    GET /liquidaciones/generales/{id}/detalle returns 200 for valid ID.
    """
    liquidacion_id = liquidacion_edificacion_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_general_detail_response_has_polymorphic_structure(
    auth_client,
    liquidacion_edificacion_for_detail,
):
    """
    Response has the polymorphic structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    liquidacion_id = liquidacion_edificacion_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

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
def test_general_detail_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_edificacion_for_detail,
):
    """
    liquidacion_general wrapper has all expected fields.
    """
    liquidacion_id = liquidacion_edificacion_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

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
def test_general_detail_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_edificacion_for_detail,
):
    """
    For EDIFICACION tipo, liquidacion_tipo has PO calculation fields.
    """
    liquidacion_id = liquidacion_edificacion_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt


@pytest.mark.django_db
def test_general_detail_endpoint_returns_404_for_invalid_id(
    auth_client,
    db,
):
    """
    GET /liquidaciones/generales/{non_existent_id}/detalle returns 404.
    Uses a valid UUID format that doesn't exist in the database.
    """
    non_existent_id = uuid.uuid4()
    response = auth_client.get(f"/liquidaciones/generales/{non_existent_id}/detalle")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent ID, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_general_detail_endpoint_id_matches_requested_id(
    auth_client,
    liquidacion_edificacion_for_detail,
):
    """
    The id in liquidacion_general matches the requested liquidacion_general_id.
    """
    liquidacion_id = liquidacion_edificacion_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

    assert response.status_code == 200
    data = response.json()
    lg_id_in_response = data["data"]["liquidacion_general"]["id"]

    assert str(lg_id_in_response) == str(liquidacion_id)


@pytest.mark.django_db
def test_general_detail_endpoint_works_for_hu_type(
    auth_client,
    liquidacion_hu_for_detail,
):
    """
    GET /liquidaciones/generales/{id}/detalle returns correct structure for
    HABILITACION_URBANA type (different polymorphic dispatch from EDIFICACION).
    """
    liquidacion_id = liquidacion_hu_for_detail.id
    response = auth_client.get(f"/liquidaciones/generales/{liquidacion_id}/detalle")

    assert response.status_code == 200, \
        f"Expected 200 for HU type, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]

    # Polymorphic structure should still be present
    assert "liquidacion_general" in result
    assert "liquidacion_especifica" in result
    assert "liquidacion_tipo" in result

    # liquidacion_general should have the expediente from the HU fixture
    assert result["liquidacion_general"]["expediente"] == "EXP-GEN-DETAIL-HU-001"

    # For HU type, liquidacion_tipo should have area_m2 (M2 field)
    lt = result["liquidacion_tipo"]
    assert "area_m2" in lt
