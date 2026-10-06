"""
Integration tests for PO Edge endpoints (/edge).

Tests cover:
- Edificaciones, Taludes, Impacto Vial edge creation with modo_calculo=MANUAL
- subtotal_manual distributed equally among specialties
- numero_revision validation (1, 3, 5 valid; 2 invalid)
- subtotal_manual > 0 validation
- No specialties available → 400
- Tarifa/derecho fields are null in response
- IGV and total calculated correctly
- Presenter handles nulls without error

Fixtures: shared fixtures come from conftest.py (re-exported from fixtures/).
Local fixtures specific to edge tests are defined at the bottom of the file.
"""
import pytest
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.tests.fixtures.factories import make_payload_po_edge


# ── Tests: Edificaciones Edge ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_po_edge_crear_edificaciones_modo_manual(
    auth_client,
    municipalidad,
    igv_vigente,
    derecho_porcentaje_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: vigentes especialidades for Edificaciones
    WHEN: POST /liquidaciones/edificaciones/edge with subtotal_manual
    THEN: returns 200 with modo_calculo=MANUAL and null tarifa/derecho fields.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=15000.00,
        numero_revision=1,
        expediente="EXP-EDGE-EDIF-001",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
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

    # Tarifa/derecho/porcentaje fields are null
    assert lt["tarifa_aplicada_id"] is None, \
        f"Expected tarifa_aplicada_id=null, got {lt.get('tarifa_aplicada_id')}"
    assert lt["derecho_aplicado_id"] is None, \
        f"Expected derecho_aplicado_id=null, got {lt.get('derecho_aplicado_id')}"
    assert lt["porcentaje_liquidacion"] is None, \
        f"Expected porcentaje_liquidacion=null, got {lt.get('porcentaje_liquidacion')}"

    # All details have null tarifa_aplicada
    for detalle in lt["detalles"]:
        assert detalle["tarifa_aplicada_id"] is None, \
            f"Expected detalle.tarifa_aplicada_id=null, got {detalle.get('tarifa_aplicada_id')}"


@pytest.mark.django_db
def test_po_edge_subtotal_distribuido_igual_3_especialidades(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: 3 vigentes especialidades for Edificaciones
    WHEN: POST /liquidaciones/edificaciones/edge with subtotal_manual=15000
    THEN: each detail subtotal is 5000, sum equals subtotal, IGV=2700, total=17700.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=15000.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    lt = data["liquidacion_tipo"]
    lg = data["liquidacion_general"]

    # 3 detalles (one per specialty)
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles, got {len(lt['detalles'])}"

    # Each subtotal should be 5000 (15000 / 3)
    for detalle in lt["detalles"]:
        assert Decimal(str(detalle["subtotal"])) == Decimal("5000.00"), \
            f"Expected subtotal=5000.00, got {detalle['subtotal']}"

    # Sum of detalles equals subtotal_manual
    suma_detalles = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    assert suma_detalles == Decimal("15000.00"), \
        f"Expected sum of detalles=15000.00, got {suma_detalles}"

    # IGV = 15000 * 0.18 = 2700
    igv_esperado = Decimal("2700.00")
    assert lg["sub_total"] == Decimal("15000.00")
    assert lg["total"] == Decimal("17700.00"), \
        f"Expected total=17700.00 (15000+2700), got {lg['total']}"


@pytest.mark.django_db
def test_po_edge_subtotal_no_divisible_redondeo(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: 3 vigentes especialidades for Edificaciones
    WHEN: POST /liquidaciones/edificaciones/edge with subtotal_manual=100 (not evenly divisible)
    THEN: base=33.33, remainder=0.01 absorbed by last detail.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=100.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    lt = data["liquidacion_tipo"]

    # 3 detalles
    assert len(lt["detalles"]) == 3

    # Sum of detalles must equal exactly 100.00
    suma_detalles = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    assert suma_detalles == Decimal("100.00"), \
        f"Expected sum of detalles=100.00, got {suma_detalles}"


@pytest.mark.django_db
def test_po_edge_numero_revision_1(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=1
    THEN: liquidacion_general.numero_revision == 1.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 1


@pytest.mark.django_db
def test_po_edge_numero_revision_3(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=3
    THEN: liquidacion_general.numero_revision == 3.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        numero_revision=3,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 3


@pytest.mark.django_db
def test_po_edge_numero_revision_5(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=5
    THEN: liquidacion_general.numero_revision == 5.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        numero_revision=5,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["numero_revision"] == 5


@pytest.mark.django_db
def test_po_edge_numero_revision_invalido_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: numero_revision=2 (not in {1, 3, 5})
    THEN: returns 400.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=5000.00,
        numero_revision=2,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid numero_revision, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_po_edge_subtotal_cero_retorna_400(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: subtotal_manual=0
    THEN: returns 400.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=0,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for subtotal_manual=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_po_edge_igv_y_total_calculados_correctamente(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: IGV vigente at 18%
    WHEN: POST /liquidaciones/edificaciones/edge with subtotal_manual=10000
    THEN: sub_total=10000, IGV=1800, total=11800.
    """
    # IGV fixture is at 18% (0.18)
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=10000.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["sub_total"] == Decimal("10000.00")
    assert lg["total"] == Decimal("11800.00"), \
        f"Expected total=11800.00 (10000 + 1800 IGV), got {lg['total']}"


# ── Tests: Taludes Edge ──────────────────────────────────────────────────────

@pytest.fixture
def especialidades_disponibles_taludes(db, tipo_taludes, especialidad_taludes):
    """Create LiquidacionEspecialidadDisponibles for Taludes."""
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_taludes,
            especialidad=especialidad_taludes,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
    ]


@pytest.mark.django_db
def test_po_edge_crear_taludes_modo_manual(
    auth_client,
    municipalidad,
    igv_vigente,
    derecho_porcentaje_vigente,
    especialidades_disponibles_taludes,
):
    """
    GIVEN: vigentes especialidades for Taludes
    WHEN: POST /liquidaciones/taludes/edge with subtotal_manual
    THEN: returns 200 with modo_calculo=MANUAL.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=8000.00,
        numero_revision=1,
        expediente="EXP-EDGE-TAL-001",
    )
    response = auth_client.post(
        "/liquidaciones/taludes/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["modo_calculo"] == "MANUAL"
    assert lg["numero_revision"] == 1


# ── Tests: Impacto Vial Edge ─────────────────────────────────────────────────

@pytest.fixture
def especialidades_disponibles_iv(db, tipo_impacto_vial, especialidad_impacto_vial):
    """Create LiquidacionEspecialidadDisponibles for Impacto Vial."""
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_impacto_vial,
            especialidad=especialidad_impacto_vial,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
    ]


@pytest.mark.django_db
def test_po_edge_crear_impacto_vial_modo_manual(
    auth_client,
    municipalidad,
    igv_vigente,
    derecho_porcentaje_vigente,
    especialidades_disponibles_iv,
):
    """
    GIVEN: vigentes especialidades for Impacto Vial
    WHEN: POST /liquidaciones/impacto-vial/edge with subtotal_manual
    THEN: returns 200 with modo_calculo=MANUAL.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=6000.00,
        numero_revision=1,
        expediente="EXP-EDGE-IV-001",
    )
    response = auth_client.post(
        "/liquidaciones/impacto-vial/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["modo_calculo"] == "MANUAL"
    assert lg["numero_revision"] == 1


# ── Tests: Distribution with 2 specialties ────────────────────────────────────

@pytest.fixture
def dos_especialidades_edificacion(db, tipo_edificacion, especialidad_estructuras, especialidad_arquitectura):
    """Create only 2 LiquidacionEspecialidadDisponibles for Edificaciones."""
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=esp,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        for esp in [especialidad_estructuras, especialidad_arquitectura]
    ]


@pytest.mark.django_db
def test_po_edge_subtotal_distribuido_igual_2_especialidades(
    auth_client,
    municipalidad,
    igv_vigente,
    dos_especialidades_edificacion,
):
    """
    GIVEN: 2 vigentes especialidades for Edificaciones
    WHEN: POST /liquidaciones/edificaciones/edge with subtotal_manual=10000
    THEN: each detail subtotal is 5000, sum equals 10000.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=10000.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    lt = data["liquidacion_tipo"]

    assert len(lt["detalles"]) == 2, \
        f"Expected 2 detalles, got {len(lt['detalles'])}"

    for detalle in lt["detalles"]:
        assert Decimal(str(detalle["subtotal"])) == Decimal("5000.00"), \
            f"Expected subtotal=5000.00, got {detalle['subtotal']}"

    suma_detalles = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    assert suma_detalles == Decimal("10000.00"), \
        f"Expected sum of detalles=10000.00, got {suma_detalles}"


# ── Tests: Presenter null-safety ─────────────────────────────────────────────

@pytest.mark.django_db
def test_po_edge_presenter_repone_null_sin_error(
    auth_client,
    municipalidad,
    igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: valid edge payload
    WHEN: presenter transforms the result with null fields
    THEN: no error is raised and all expected fields are present in response.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=7500.00,
        numero_revision=1,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
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
    assert lt["porcentaje_liquidacion"] is None
    assert lt["derecho_aplicado_id"] is None
    assert lt["tarifa_aplicada_id"] is None

    # Verify detalles exist with null fields
    assert len(lt["detalles"]) > 0
    for detalle in lt["detalles"]:
        assert detalle["tarifa_aplicada_id"] is None
        assert detalle["porcentaje_aplicado"] is None
