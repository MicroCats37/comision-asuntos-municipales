"""
Integration tests for Edificaciones /nueva-liquidacion/primera-revision endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Fixtures: All shared fixtures come from conftest.py (tests/conftest.py), which
re-exports from tests/fixtures/*. Fixtures that are local to this file (not shared)
are defined at the bottom of the file.

Tests cover:
- Hybrid mode (auto-fill empty array)
- Explicit mode (3 tarifas sent)
- Validation errors (valor_declarado <= 0, invalid tarifa, wrong type)
- Clamping (minimum applied when total < derecho_minimo)
- tipo_tramite is NULL in response
- 3 wrappers in response structure
- Snapshot values preserved (igv_id, uit_id)
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)

from modules.liquidaciones.tests.fixtures.factories import make_payload_po


# ── Local-only fixtures (not in conftest) ────────────────────────────────────

@pytest.fixture
def tarifa_porcentaje_obra_base2(db, tipo_edificacion):
    """Second TarifaLiquidacionBase + TarifaPorcentajeObra for explicit mode test."""
    base2 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base2,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_base3(db, tipo_edificacion):
    """Third TarifaLiquidacionBase + TarifaPorcentajeObra for explicit mode test."""
    base3 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base3,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_happy_path_auto_fill_mode(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidades_disponibles_edificacion,
):
    """
    Auto-fill: empty tarifas[] → backend picks all vigentes.

    The /nueva-liquidacion/primera-revision endpoint accepts a payload with
    empty tarifas[] and returns 200, auto-filling all vigentes.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-001",
        valor_declarado=100000.00,
        tarifas=None,  # auto-fill mode
        observacion="Test auto-fill mode",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "liquidacion_general" in result
    assert "liquidacion_tipo" in result
    assert "liquidacion_especifica" in result

    # Verify liquidacion_general has expected fields
    lg = result["liquidacion_general"]
    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert lg["expediente"] == "EXP-EDIF-2024-001"
    assert lg["numero_revision"] == 1

    # Verify liquidacion_especifica has identity fields
    le = result["liquidacion_especifica"]
    assert "id" in le
    assert "numero" in le

    # Verify liquidacion_tipo has calculation fields
    lt = result["liquidacion_tipo"]
    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt

    # Should have 3 detalles (one per auto-filled tarifa)
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles for auto-fill mode, got {len(lt['detalles'])}"


@pytest.mark.django_db
def test_happy_path_explicit_mode(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, especialidad_estructuras, especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    Explicit: 3 tarifa_ids sent → backend validates each.

    The /nueva-liquidacion/primera-revision endpoint accepts a payload with
    explicit tarifa_ids and returns 200 with those exact tarifas.
    """
    tarifas_explicit = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-002",
        valor_declarado=100000.00,
        tarifas=tarifas_explicit,
        observacion="Test explicit mode",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]

    lt = result["liquidacion_tipo"]
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles for explicit mode, got {len(lt['detalles'])}"

    # Verify percentages are correct: 0.0010 + 0.0005 + 0.0003 = 0.0018
    total_porcentaje = sum(Decimal(str(d["porcentaje_aplicado"])) for d in lt["detalles"])
    assert abs(total_porcentaje - Decimal("0.0018")) < Decimal("0.0001"), \
        f"Expected total porcentaje 0.0018, got {total_porcentaje}"


@pytest.mark.django_db
def test_valor_declarado_zero_returns_400(
    auth_client, municipalidad,
):
    """
    Validation: valor_declarado = 0 → HttpError 400.

    The orchestrator validates that valor_declarado must be > 0.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-VALID-001",
        valor_declarado=0,  # Invalid
        tarifas=None,
        observacion=None,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for valor_declarado=0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_valor_declarado_negative_returns_400(
    auth_client, municipalidad,
):
    """
    Validation: valor_declarado < 0 → HttpError 400.

    The orchestrator validates that valor_declarado must be > 0.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-VALID-002",
        valor_declarado=-1000.00,  # Invalid
        tarifas=None,
        observacion=None,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for valor_declarado < 0, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_invalid_tarifa_id_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
):
    """
    Validation: non-existent tarifa_id → HttpError 400.

    When an explicit tarifa_id doesn't exist, the orchestrator raises HttpError 400.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-VALID-003",
        valor_declarado=100000.00,
        tarifas=[
            {"tarifa_porcentaje_obra_id": str(uuid.uuid4()), "especialidad_id": str(uuid.uuid4())},  # Non-existent
        ],
        observacion=None,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for invalid tarifa_id, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_tarifa_wrong_type_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_liquidacion_base_edificacion, tipo_habilitacion_urbana
):
    """
    Validation: HU tarifa sent → HttpError 400 'no es de edificaciones'.

    When a tariff of a different tipo_liquidacion is sent, the orchestrator
    raises HttpError 400 with message 'no es de edificaciones'.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import TarifaPorMetroCuadrado

    hu_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    hu_tarifa = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=hu_tarifa_base,
        costo_por_m2=Decimal("150.0000"),
    )

    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-VALID-004",
        valor_declarado=100000.00,
        tarifas=[
            {"tarifa_porcentaje_obra_id": str(hu_tarifa.id), "especialidad_id": str(uuid.uuid4())},  # Wrong type!
        ],
        observacion=None,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for wrong tipo_liquidacion, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_tarifa_not_vigente_returns_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tipo_edificacion
):
    """
    Validation: expired tarifa → HttpError 400 'no está vigente'.

    When a tariff is expired (has periodo_fin), the orchestrator raises
    HttpError 400 with message 'no está vigente'.
    """
    expired_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 12, 31),  # Expired
    )
    expired_tarifa = TarifaPorcentajeObra.objects.create(
        tarifa_base=expired_tarifa_base,
        porcentaje_liquidacion=Decimal("0.0010"),
    )

    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-VALID-005",
        valor_declarado=100000.00,
        tarifas=[
            {"tarifa_porcentaje_obra_id": str(expired_tarifa.id), "especialidad_id": str(uuid.uuid4())},
        ],
        observacion=None,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400 for expired tarifa, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_response_has_three_wrappers(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    Response structure: liquidacion_general + especifica + tipo.

    The primera-revision endpoint returns LiquidacionEdificacionesOutput which
    is the union of the three wrappers.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-WRAPPERS",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test three wrappers",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]

    # Validate all three top-level wrappers are present
    assert "liquidacion_general" in result, \
        "Response should have 'liquidacion_general' wrapper"
    assert "liquidacion_tipo" in result, \
        "Response should have 'liquidacion_tipo' wrapper"
    assert "liquidacion_especifica" in result, \
        "Response should have 'liquidacion_especifica' wrapper"


@pytest.mark.django_db
def test_liquidacion_especifica_is_identity(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    liquidacion_especifica wrapper has only id + numero.

    Semantically: especifica = identity wrapper (id + auto-generated numero).
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-IDENTITY",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test identity",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    le = result["liquidacion_especifica"]

    # Validate identity structure
    assert "id" in le, "liquidacion_especifica should have 'id'"
    assert "numero" in le, "liquidacion_especifica should have 'numero'"

    # Should NOT have calculation fields
    assert "valor_declarado" not in le, \
        "liquidacion_especifica should NOT have 'valor_declarado' (that's in liquidacion_tipo)"
    assert "detalles" not in le, \
        "liquidacion_especifica should NOT have 'detalles' (that's in liquidacion_tipo)"


@pytest.mark.django_db
def test_liquidacion_tipo_has_detalles(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidades_disponibles_edificacion,
):
    """
    liquidacion_tipo.detalles has N entries (one per tarifa).

    Each detail has: id, tarifa_aplicada_id, especialidad_id, porcentaje_aplicado,
    subtotal, igv, uit, total.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-DETALLES",
        valor_declarado=100000.00,
        tarifas=None,  # auto-fill
        observacion="Test detalles",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    assert "detalles" in lt, "liquidacion_tipo should have 'detalles'"
    assert len(lt["detalles"]) == 3, \
        f"Expected 3 detalles (one per tarifa), got {len(lt['detalles'])}"

    # Verify each detalle has required fields
    for detalle in lt["detalles"]:
        assert "id" in detalle
        assert "tarifa_aplicada_id" in detalle
        assert "especialidad_id" in detalle
        assert "porcentaje_aplicado" in detalle
        assert "subtotal" in detalle


@pytest.mark.django_db
def test_subtotal_is_sum_of_detalles(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidades_disponibles_edificacion,
):
    """
    LiquidacionGeneral.sub_total = SUM(detalles.subtotal).

    The subtotal of the liquidacion_general should equal the sum of all detail subtotals.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-SUBTOTAL",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test subtotal",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # Sum of detalle subtotals
    expected_subtotal = sum(Decimal(str(d["subtotal"])) for d in lt["detalles"])
    actual_subtotal = Decimal(str(lg["sub_total"]))

    assert abs(expected_subtotal - actual_subtotal) < Decimal("0.01"), \
        f"Expected sub_total={expected_subtotal}, got {actual_subtotal}"


@pytest.mark.django_db
def test_total_calculation_with_igv(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    LiquidacionGeneral.total = sub_total + IGV.

    With IGV = 18%, total should be sub_total * 1.18.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-IGV",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test IGV",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    sub_total = Decimal(str(lg["sub_total"]))
    total = Decimal(str(lg["total"]))
    igv = lg["igv"]

    # If igv is set, total should include IGV
    if igv is not None:
        expected_total = sub_total * Decimal("1.18")
        assert abs(expected_total - total) < Decimal("0.01"), \
            f"Expected total={expected_total} (sub_total * 1.18), got {total}"
    else:
        # If no IGV, total should equal sub_total
        assert abs(sub_total - total) < Decimal("0.01"), \
            f"Expected total=sub_total when no IGV, got total={total}"


@pytest.mark.django_db
def test_tipo_tramite_is_null(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    tipo_tramite field is None in response.

    Currently tipo_tramite stays NULL for all liquidations (FUTURE: activate when frontend sends it).
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-NULL-TRAMITE",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test tipo_tramite null",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    assert lt["tipo_tramite"] is None, \
        f"Expected tipo_tramite to be None, got {lt['tipo_tramite']}"


@pytest.mark.django_db
def test_clamping_minimum_applied(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
):
    """
    When total < derecho_minimo, clamp to min + distribute proportionally.

    With derecho_minimo = 500.00 and a very small valor_declarado that would result
    in a subtotal below 500, the system should clamp to derecho_minimo.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-CLAMP-MIN",
        valor_declarado=1000.00,  # Small value, will result in < 500 subtotal
        tarifas=[
            {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        ],
        observacion="Test clamping minimum",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # The total should be clamped to derecho_minimo (500.00)
    # Note: exact behavior depends on implementation (proportional distribution or fixed minimum)
    # At minimum, sub_total and total should be >= derecho_minimo
    assert lg["sub_total"] >= 500.00, \
        f"Expected sub_total >= 500.00 (derecho_minimo), got {lg['sub_total']}"
    assert lg["total"] >= 500.00, \
        f"Expected total >= 500.00 (derecho_minimo), got {lg['total']}"


@pytest.mark.django_db
def test_porcentaje_liquidacion_is_sum(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, especialidad_estructuras, especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    porcentaje_liquidacion = SUM of all tarifa percentages.

    The percentage_liquidacion in liquidacion_tipo should equal the sum of
    all applied tarifa percentages.
    """
    tarifas_explicit = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-PCT-SUM",
        valor_declarado=100000.00,
        tarifas=tarifas_explicit,
        observacion="Test porcentaje sum",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    # Sum of expected percentages: 0.0010 + 0.0005 + 0.0003 = 0.0018
    expected_porcentaje = Decimal("0.0010") + Decimal("0.0005") + Decimal("0.0003")
    actual_porcentaje = Decimal(str(lt["porcentaje_liquidacion"]))

    assert abs(expected_porcentaje - actual_porcentaje) < Decimal("0.0001"), \
        f"Expected porcentaje_liquidacion={expected_porcentaje}, got {actual_porcentaje}"


@pytest.mark.django_db
def test_snapshot_igv_uit_assigned(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    igv_id and uit_id are populated in LiquidacionGeneral.

    The primera-revision endpoint should populate igv_id and uit_id as FK references
    from the configured IGV and UIT vigente.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-EDIF-2024-SNAPSHOT",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test igv/uit snapshot",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]

    # Verify igv and uit are present (they may be None if no IGV/UIT is configured)
    assert "igv" in lg, "liquidacion_general should have 'igv' field"
    assert "uit" in lg, "liquidacion_general should have 'uit' field"

    # If igv is not None, verify it's an object with valid UUID id
    if lg["igv"] is not None:
        igv_uuid = uuid.UUID(str(lg["igv"]["id"]))
        assert isinstance(igv_uuid, uuid.UUID), \
            f"igv.id should be a valid UUID, got {lg['igv']['id']}"

    # If uit is not None, verify it's an object with valid UUID id
    if lg["uit"] is not None:
        uit_uuid = uuid.UUID(str(lg["uit"]["id"]))
        assert isinstance(uit_uuid, uuid.UUID), \
            f"uit.id should be a valid UUID, got {lg['uit']['id']}"


@pytest.mark.django_db
def test_crear_liquidacion_con_contacto_inline(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """Crea una liquidacion con contacto inline y verifica que el output lo incluya anidado."""
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-CONTACTO-001",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test contacto inline",
        contacto={
            "nombres": "MARIA CONTACTO",
            "apellidos": "GARCIA PEREZ",
            "dni": "87654321",
            "cargo": "PROPIETARIA",
            "celular": "999888777",
        },
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]

    assert lg["contacto"] is not None, "El output debe incluir contacto anidado"
    assert lg["contacto"]["nombres"] == "MARIA CONTACTO"
    assert lg["contacto"]["apellidos"] == "GARCIA PEREZ"
    assert lg["contacto"]["dni"] == "87654321"
    assert lg["contacto"]["cargo"] == "PROPIETARIA"


@pytest.mark.django_db
def test_crear_liquidacion_sin_contacto(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
):
    """Sin contacto en el input, el output debe traer contacto=None."""
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-NO-CONTACTO-001",
        valor_declarado=100000.00,
        tarifas=None,
        observacion="Test sin contacto",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]

    assert lg["contacto"] is None, "Sin contacto en input, output debe ser None"
