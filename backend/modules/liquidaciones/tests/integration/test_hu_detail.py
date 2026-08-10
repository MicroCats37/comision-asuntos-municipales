"""
Integration tests for Habilitacion Urbana GET /{id} detail endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /{liquidacion_id} returns 200 with LiquidacionHabilitacionUrbanaOutput structure
- GET /{liquidacion_id} returns 404 for non-existent ID
- Response matches the expected output schema

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
import uuid
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_hu(db):
    """Create a TarifaLiquidacionBase for Habilitacion Urbana."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_vigente(db, tarifa_liquidacion_base_hu):
    """Create a TarifaPorMetroCuadrado for Habilitacion Urbana."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_hu,
        costo_por_m2=Decimal("50.00"),
    )


@pytest.fixture
def derecho_m2_vigente(db):
    """Create a DerechoPorMetroCuadrado vigente for testing."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_hu_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_m2_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_m2_vigente,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionHabilitacionUrbana + LiquidacionPorMetroCuadrado
    for testing the detail endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-HU-DETAIL-001",
        observacion="Test liquidation HU for detail",
        estado="PENDIENTE",
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        numero_revision=1,
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionHabilitacionUrbana (identity)
    hu = LiquidacionHabilitacionUrbana.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorMetroCuadrado
    m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("100.00"),
        costo_por_m2=tarifa_m2_vigente.costo_por_m2,
        derecho_minimo=derecho_m2_vigente.derecho_minimo,
        derecho_maximo=derecho_m2_vigente.derecho_maximo,
        tarifa_aplicada=tarifa_m2_vigente,
        derecho=derecho_m2_vigente,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detail_endpoint_returns_200(
    auth_client,
    liquidacion_hu_detail,
):
    """
    GET /liquidaciones/habilitacion-urbana/{liquidacion_id} returns 200 for valid ID.
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_response_has_liquidacion_hu_output_structure(
    auth_client,
    liquidacion_hu_detail,
):
    """
    Response has the LiquidacionHabilitacionUrbanaOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

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
    liquidacion_hu_detail,
):
    """
    liquidacion_general wrapper has all expected fields.
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lg = data["data"]["liquidacion_general"]

    assert "id" in lg
    assert "municipalidad_id" in lg
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
    liquidacion_hu_detail,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    Should NOT have area_m2 (that's in liquidacion_tipo).
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

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
    liquidacion_hu_detail,
):
    """
    liquidacion_tipo wrapper has calculation fields: area_m2, costo_por_m2, etc.
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "area_m2" in lt
    assert "costo_por_m2" in lt
    assert "derecho_minimo" in lt
    assert "tarifa_aplicada_id" in lt
    assert "derecho_aplicado_id" in lt


@pytest.mark.django_db
def test_detail_endpoint_returns_404_for_invalid_id(
    auth_client,
    db,
):
    """
    GET /liquidaciones/habilitacion-urbana/{non_existent_id} returns 404.
    Uses a valid UUID format that doesn't exist in the database.
    """
    non_existent_id = uuid.uuid4()
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{non_existent_id}")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent ID, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_endpoint_returns_404_for_wrong_type_liquidacion(
    auth_client,
    db,
    municipalidad,
    proyecto,
    create_user,
):
    """
    GET /liquidaciones/habilitacion-urbana/{id_of_different_type} returns 404.
    This creates a liquidacion of a different type (Edificacion) and
    verifies that requesting it via the HU endpoint returns 404.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
        LiquidacionEdificacion,
    )
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
        LiquidacionPorcentajeObra,
    )
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
        TarifaPorcentajeObra,
        DerechoPorcentajeObra,
    )
    from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
    from modules.usuarios.domain.models.perfil_ingeniero import Especialidad

    user = create_user

    # Create TarifaLiquidacionBase for Edificacion
    tarifa_base_edif = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )

    # Create especialidad
    especialidad = Especialidad.objects.create(
        codigo="E01",
        nombre="Estructuras",
    )

    # Create TarifaPorcentajeObra
    tarifa_pct = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_edif,
        especialidad=especialidad,
        porcentaje_liquidacion=Decimal("0.0010"),
    )

    # Create DerechoPorcentajeObra
    derecho_pct = DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio="2024-01-01",
        periodo_fin=None,
    )

    # Create Edificacion liquidacion
    edif_lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-EDIF-001",
        estado="PENDIENTE",
        tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )

    # Create LiquidacionEdificacion (identity)
    LiquidacionEdificacion.objects.create(
        liquidacion=edif_lg,
        numero=1,
    )

    # Create LiquidacionPorcentajeObra
    LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=edif_lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_pct,
    )

    # Try to fetch it via HU endpoint - should return 404
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{edif_lg.id}")

    assert response.status_code == 404, \
        f"Expected 404 when fetching Edificacion liquidacion via HU endpoint, got {response.status_code}"


@pytest.mark.django_db
def test_detail_id_matches_output_liquidacion_general_id(
    auth_client,
    liquidacion_hu_detail,
):
    """
    The id in liquidacion_general matches the requested liquidacion_id.
    """
    liquidacion_id = liquidacion_hu_detail.id
    response = auth_client.get(f"/liquidaciones/habilitacion-urbana/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lg_id_in_response = data["data"]["liquidacion_general"]["id"]

    # The ID returned should match the requested ID
    assert str(lg_id_in_response) == str(liquidacion_id)
