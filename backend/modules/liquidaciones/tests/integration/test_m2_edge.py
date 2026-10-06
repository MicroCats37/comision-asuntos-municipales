"""
Integration tests for M2 Edge endpoints (/edge).

Tests cover:
- Habilitación Urbana and Mecánica de Suelos edge creation with modo_calculo=MANUAL
- subtotal_manual as pre-IGV subtotal; IGV and total calculated by backend
- numero_revision validation (1, 3, 5 valid; 2, 4 invalid)
- subtotal_manual > 0 validation (domain returns 400, not schema 422)
- area_m2 for traceability (>= 0)
- Tarifa/derecho/costo_por_m2 fields are null in response
- IGV calculated correctly (subtotal * igv_porcentaje)
- Normal TARIFA flow remains intact

Fixtures: shared fixtures come from conftest.py (re-exported from fixtures/).
Local fixtures specific to edge tests are defined at the bottom of the file.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.tests.fixtures.factories import make_payload_m2_edge


@pytest.fixture(autouse=True)
def m2_edge_tipo_liquidacion_setup(tipo_habilitacion_urbana, tipo_mecanica_suelos):
    """Ensure edge tests always have the M2 TipoLiquidacion rows available."""


# ── Tests: Habilitación Urbana Edge ─────────────────────────────────────────────

@pytest.mark.django_db
def test_m2_edge_crear_habilitacion_urbana_modo_manual(
    auth_client,
    municipalidad,
    igv_vigente,
    tipo_habilitacion_urbana,
):
    """
    GIVEN: valid IGV vigente
    WHEN: POST /liquidaciones/habilitacion-urbana/edge with subtotal_manual
    THEN: returns 200 with modo_calculo=MANUAL and null tarifa/derecho fields.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=15000.00,
        area_m2=250.0,
        numero_revision=1,
        expediente="EXP-EDGE-HU-001",
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    lg = data["liquidacion_general"]
    lt = data["liquidacion_tipo"]

    # modo_calculo is MANUAL
    assert lg["modo_calculo"] == "MANUAL", \
        f"Expected modo_calculo=MANUAL, got {lg.get('modo_calculo')}"

    # numero_revision is preserved
    assert lg["numero_revision"] == 1

    # Tarifa/derecho/costo_por_m2 fields are null
    assert lt["tarifa_aplicada_id"] is None, \
        f"Expected tarifa_aplicada_id=null, got {lt.get('tarifa_aplicada_id')}"
    assert lt["derecho_aplicado_id"] is None, \
        f"Expected derecho_aplicado_id=null, got {lt.get('derecho_aplicado_id')}"
    assert lt["costo_por_m2"] is None, \
        f"Expected costo_por_m2=null, got {lt.get('costo_por_m2')}"


@pytest.mark.django_db
def test_m2_edge_igv_y_total_calculados_correctamente(
    auth_client,
    municipalidad,
    igv_vigente,
    tipo_habilitacion_urbana,
):
    """
    GIVEN: IGV vigente at 18%
    WHEN: POST /liquidaciones/habilitacion-urbana/edge with subtotal_manual=10000
    THEN: sub_total=10000, IGV=1800, total=11800.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=10000.00,
        area_m2=100.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["sub_total"] == Decimal("10000.00")
    assert lg["total"] == Decimal("11800.00"), \
        f"Expected total=11800.00 (10000 + 1800 IGV), got {lg['total']}"


@pytest.mark.django_db
def test_m2_edge_numero_revision_1(
    auth_client,
    municipalidad,
    igv_vigente,
    tipo_habilitacion_urbana,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=1
    THEN: liquidacion_general.numero_revision == 1.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=50.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 1


@pytest.mark.django_db
def test_m2_edge_numero_revision_3(
    auth_client,
    municipalidad,
    igv_vigente,
    tipo_habilitacion_urbana,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=3
    THEN: liquidacion_general.numero_revision == 3.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=50.0,
        numero_revision=3,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 3


@pytest.mark.django_db
def test_m2_edge_numero_revision_5(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=5
    THEN: liquidacion_general.numero_revision == 5.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=50.0,
        numero_revision=5,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 5


@pytest.mark.django_db
def test_m2_edge_numero_revision_invalido_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=2 (not in {1, 3, 5})
    THEN: returns 400.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=50.0,
        numero_revision=2,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid numero_revision, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_m2_edge_numero_revision_4_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=4 (not in {1, 3, 5})
    THEN: returns 400.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=50.0,
        numero_revision=4,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid numero_revision, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_m2_edge_subtotal_cero_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: subtotal_manual=0
    THEN: returns 400 (domain validation, not schema 422).
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=0,
        area_m2=50.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for subtotal_manual=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_m2_edge_subtotal_negativo_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: subtotal_manual=-100
    THEN: returns 400.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=-100.00,
        area_m2=50.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for negative subtotal_manual, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_m2_edge_presenter_handles_nulls_sin_error(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: presenter transforms the result with null fields
    THEN: no error is raised and all expected fields are present in response.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=7500.00,
        area_m2=75.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]

    # Verify all expected wrappers are present
    assert "liquidacion_general" in data
    assert "liquidacion_especifica" in data
    assert "liquidacion_tipo" in data

    # Verify null fields are present (not missing)
    lt = data["liquidacion_tipo"]
    assert lt["tarifa_aplicada_id"] is None
    assert lt["derecho_aplicado_id"] is None
    assert lt["costo_por_m2"] is None

    # Verify area_m2 is preserved
    assert Decimal(str(lt["area_m2"])) == Decimal("75.0")


@pytest.mark.django_db
def test_m2_edge_area_m2_cero_aceptado(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid edge payload
    WHEN: area_m2=0 (allowed for edge)
    THEN: returns 200.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200 for area_m2=0, got {response.status_code}: {response.content}"


# ── Tests: Mecánica de Suelos Edge ──────────────────────────────────────────────

@pytest.mark.django_db
def test_m2_edge_crear_mecanica_suelos_modo_manual(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid IGV vigente
    WHEN: POST /liquidaciones/mecanica-suelos/edge with subtotal_manual
    THEN: returns 200 with modo_calculo=MANUAL and null tarifa/derecho fields.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=12000.00,
        area_m2=200.0,
        numero_revision=1,
        expediente="EXP-EDGE-MS-001",
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    lg = data["liquidacion_general"]
    lt = data["liquidacion_tipo"]

    assert lg["modo_calculo"] == "MANUAL"
    assert lg["numero_revision"] == 1
    assert lt["tarifa_aplicada_id"] is None
    assert lt["derecho_aplicado_id"] is None
    assert lt["costo_por_m2"] is None


@pytest.mark.django_db
def test_m2_edge_ms_igv_y_total_calculados_correctamente(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: IGV vigente at 18%
    WHEN: POST /liquidaciones/mecanica-suelos/edge with subtotal_manual=5000
    THEN: sub_total=5000, IGV=900, total=5900.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        area_m2=80.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["sub_total"] == Decimal("5000.00")
    assert lg["total"] == Decimal("5900.00"), \
        f"Expected total=5900.00 (5000 + 900 IGV), got {lg['total']}"


@pytest.mark.django_db
def test_m2_edge_ms_numero_revision_3(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid MS edge payload
    WHEN: numero_revision=3
    THEN: liquidacion_general.numero_revision == 3.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=8000.00,
        area_m2=120.0,
        numero_revision=3,
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 3


@pytest.mark.django_db
def test_m2_edge_ms_numero_revision_invalido_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid MS edge payload
    WHEN: numero_revision=2 (not in {1, 3, 5})
    THEN: returns 400.
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=8000.00,
        area_m2=120.0,
        numero_revision=2,
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid numero_revision, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_m2_edge_ms_subtotal_cero_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
):
    """
    GIVEN: valid MS edge payload
    WHEN: subtotal_manual=0
    THEN: returns 400 (domain validation).
    """
    payload = make_payload_m2_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=0,
        area_m2=120.0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for subtotal_manual=0, got {response.status_code}: {response.content}"
