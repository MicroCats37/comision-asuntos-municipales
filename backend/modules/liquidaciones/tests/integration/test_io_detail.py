"""
Integration tests for Inspección de Obra GET /{id} detail endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /{liquidacion_id} returns 200 with LiquidacionInspeccionObraOutput structure
- GET /{liquidacion_id} returns 404 for non-existent ID
- GET /{liquidacion_id} returns 404 for wrong type liquidacion
- Response matches the expected output schema

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
import uuid
from datetime import date
from decimal import Decimal
from django.db import connection

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_io_detail(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tipo_inspeccion_obra,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionInspeccionObra + LiquidacionPorCategoriaVisitas
    for testing the detail endpoint.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-DETAIL-001",
        observacion="Test liquidation IO for detail",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("772.50"),
        total=Decimal("911.55"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionInspeccionObra (identity wrapper)
    io = LiquidacionInspeccionObra.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorCategoriaVisitas (calculation data)
    lv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detail_endpoint_returns_200(
    auth_client,
    liquidacion_io_detail,
):
    """
    GET /liquidaciones/inspeccion-obra/{liquidacion_id} returns 200 for valid ID.
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_detail_response_has_liquidacion_io_output_structure(
    auth_client,
    liquidacion_io_detail,
):
    """
    Response has the LiquidacionInspeccionObraOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

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
    liquidacion_io_detail,
):
    """
    liquidacion_general wrapper has all expected fields.
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

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
    liquidacion_io_detail,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    Should NOT have cantidad_visitas (that's in liquidacion_tipo).
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    le = data["data"]["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "cantidad_visitas" not in le, \
        "liquidacion_especifica should NOT have cantidad_visitas"


@pytest.mark.django_db
def test_detail_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_io_detail,
):
    """
    liquidacion_tipo wrapper has calculation fields: cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id.
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "id" in lt
    assert "cantidad_visitas" in lt
    assert "porcentaje_uit" in lt
    assert "categoria" in lt
    assert "tarifa_aplicada_id" in lt


@pytest.mark.django_db
def test_detail_liquidacion_tipo_has_registros_pago_field(
    auth_client,
    liquidacion_io_detail,
):
    """
    liquidacion_tipo wrapper includes persisted RegistroPagoInspector rows.
    """
    liquidacion_visitas = liquidacion_io_detail.liquidacion_visitas.first()
    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=9,
        inspecciones_pagadas=2,
        fecha_registro=date(2026, 9, 25),
    )

    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lt = data["data"]["liquidacion_tipo"]

    assert "registros_pago" in lt
    assert isinstance(lt["registros_pago"], list)
    assert lt["registros_pago"] == [
        {
            "id": str(liquidacion_visitas.registros_pago.first().id),
            "periodo": 2026,
            "mes": 9,
            "inspecciones_pagadas": 2,
            "fecha_registro": "2026-09-25",
        }
    ]


@pytest.mark.django_db
def test_detail_liquidacion_tipo_normalizes_legacy_periodo_string(
    auth_client,
    liquidacion_io_detail,
):
    """
    Legacy SQLite data can contain periodo as 'YYYY-MM'; output normalizes it.
    """
    liquidacion_visitas = liquidacion_io_detail.liquidacion_visitas.first()
    registro = RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=None,
        inspecciones_pagadas=1,
        fecha_registro=date(2026, 9, 25),
    )
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {RegistroPagoInspector._meta.db_table} SET periodo = %s WHERE id = %s",
            ["2026-09", str(registro.id)],
        )

    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_io_detail.id}")

    assert response.status_code == 200
    registro_out = response.json()["data"]["liquidacion_tipo"]["registros_pago"][0]
    assert registro_out["periodo"] == 2026
    assert registro_out["mes"] == 9


@pytest.mark.django_db
def test_detail_endpoint_returns_404_for_invalid_id(
    auth_client,
    db,
):
    """
    GET /liquidaciones/inspeccion-obra/{non_existent_id} returns 404.
    Uses a valid UUID format that doesn't exist in the database.
    """
    non_existent_id = uuid.uuid4()
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{non_existent_id}")

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
    GET /liquidaciones/inspeccion-obra/{id_of_different_type} returns 404.
    This creates a liquidacion of a different type (Habilitacion Urbana) and
    verifies that requesting it via the IO endpoint returns 404.
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

    # Try to fetch it via IO endpoint - should return 404
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{hu_lg.id}")

    assert response.status_code == 404, \
        f"Expected 404 when fetching HU liquidacion via IO endpoint, got {response.status_code}"


@pytest.mark.django_db
def test_detail_id_matches_output_liquidacion_general_id(
    auth_client,
    liquidacion_io_detail,
):
    """
    The id in liquidacion_general matches the requested liquidacion_id.
    """
    liquidacion_id = liquidacion_io_detail.id
    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200
    data = response.json()
    lg_id_in_response = data["data"]["liquidacion_general"]["id"]

    # The ID returned should match the requested ID
    assert str(lg_id_in_response) == str(liquidacion_id)
