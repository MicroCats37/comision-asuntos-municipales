"""
Integration tests for the EDIT COMPATIBILITY of legacy records
(Phase 3, task 3.2 — "Existing edit must preserve legacy/date").

Requirement (MODIFIED — Edit compatibility): the current edit flows MUST
accept normal and legacy records, MUST preserve the stored `legacy` flag and
MUST resolve the calculations from the persisted `fecha_registro`.

What this file proves:
- editing the general block of a LEGACY record keeps `legacy=true` and the
  historical `fecha_registro`;
- the recalculation of a legacy record uses the PERSISTED date (historical
  IGV/UIT/tarifas), not today's;
- editing a NORMAL record keeps `legacy=false` and its own date — the
  no-date behavior stays current.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.tests.fixtures.factories import (
    make_patch_po_estrategia,
    make_patch_wrapper_general_payload,
    make_payload_legacy_m2,
    make_payload_legacy_po,
    make_payload_po,
    make_payload_po_edge,
)


def _dec(valor) -> Decimal:
    """Normaliza un decimal de la API a `Decimal` (la API puede serializar texto o float)."""
    return Decimal(str(valor))


def _crear_legacy_po(auth_client, municipalidad, catalogo, numero, valor_declarado=1000000.00):
    """Crea un registro legacy de Edificaciones y devuelve los wrappers."""
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=numero,
        fecha_registro=catalogo["fecha_registro"],
        valor_declarado=valor_declarado,
        expediente="EXP-EDIT-LEGACY-001",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=payload,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    return response.json()["data"]


# ── El flag y la fecha sobreviven a la edición ──────────────────────────────

@pytest.mark.django_db
def test_editar_registro_legacy_conserva_el_flag_y_la_fecha(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy creado por la ruta tipada.
    WHEN:  se edita su bloque general (expediente / observacion).
    THEN:  200, `legacy` sigue en true y `fecha_registro` sigue siendo la
           histórica (no se reescribe con la fecha de la edición).
    """
    resultado = _crear_legacy_po(
        auth_client,
        municipalidad,
        catalogo_legacy_historico,
        8201,
    )
    liquidacion_id = resultado["liquidacion_general"]["id"]
    fecha_original = resultado["liquidacion_general"]["fecha_registro"]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_wrapper_general_payload(
            expediente="EXP-EDIT-LEGACY-002",
            observacion="Registro editado",
        ),
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["legacy"] is True
    assert lg["fecha_registro"] == fecha_original
    assert lg["expediente"] == "EXP-EDIT-LEGACY-002"
    assert lg["observacion"] == "Registro editado"


@pytest.mark.django_db
def test_editar_registro_legacy_m2_conserva_el_flag_y_la_fecha(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy de Habilitación Urbana.
    WHEN:  se edita su bloque general.
    THEN:  200, `legacy` sigue en true y `fecha_registro` no cambia.
    """
    payload = make_payload_legacy_m2(
        municipalidad.id,
        municipalidad.distrito_id,
        catalogo_legacy_historico["tarifa_m2_habilitacion_urbana"].id,
        numero=8202,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        expediente="EXP-EDIT-LEGACY-M2-001",
    )
    create_response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )

    datos = create_response.json()["data"]
    liquidacion_id = datos["liquidacion_general"]["id"]
    fecha_original = datos["liquidacion_general"]["fecha_registro"]

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=make_patch_wrapper_general_payload(expediente="EXP-EDIT-LEGACY-M2-002"),
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["legacy"] is True
    assert lg["fecha_registro"] == fecha_original
    assert lg["expediente"] == "EXP-EDIT-LEGACY-M2-002"


# ── El recálculo usa la fecha PERSISTIDA ────────────────────────────────────

@pytest.mark.django_db
def test_editar_registro_legacy_recalcula_con_la_fecha_persistida(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy de Edificaciones con fecha 2023-06-15.
    WHEN:  se recalcula cambiando el valor declarado.
    THEN:  el recálculo usa los valores de la fecha PERSISTIDA (tarifa 0.20 % por
           especialidad y UIT 4950), no los vigentes del día de la edición.
    """
    resultado = _crear_legacy_po(
        auth_client,
        municipalidad,
        catalogo_legacy_historico,
        8203,
    )
    liquidacion_id = resultado["liquidacion_general"]["id"]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(valor_declarado=2000000.00),
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    lg = data["liquidacion_general"]
    lt = data["liquidacion_tipo"]

    # 3 especialidades × 0.20 % (tarifa histórica) = 0.60 %
    assert _dec(lt["porcentaje_liquidacion"]) == Decimal("0.0060")
    # 2,000,000 × 0.60 % = 12,000 (por encima del piso UIT de 495)
    assert _dec(lg["sub_total"]) == Decimal("12000.00")
    assert _dec(lg["total"]) == Decimal("14160.00")
    # La UIT aplicada sigue siendo la histórica.
    assert _dec(lg["uit"]["valor"]) == Decimal("4950")
    assert lg["legacy"] is True


# ── El camino normal NO cambia ─────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_registro_normal_conserva_el_flag_y_la_fecha(
    auth_client,
    municipalidad,
    po_base_setup,
):
    """
    GIVEN: un registro NORMAL (no legacy) creado por la ruta vigente.
    WHEN:  se edita su bloque general.
    THEN:  200, `legacy` sigue en false y su `fecha_registro` no cambia — el
           comportamiento sin fecha efectiva sigue siendo el vigente.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-NORMAL-001",
        valor_declarado=1000000.00,
        tarifas=None,
        observacion="Registro normal",
    )
    create_response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )

    datos = create_response.json()["data"]
    liquidacion_id = datos["liquidacion_general"]["id"]
    fecha_original = datos["liquidacion_general"]["fecha_registro"]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_wrapper_general_payload(expediente="EXP-NORMAL-002"),
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["legacy"] is False
    assert lg["fecha_registro"] == fecha_original
    assert lg["expediente"] == "EXP-NORMAL-002"


# ── El modo MANUAL (edge) se rechaza explícitamente, no revienta ───────────

@pytest.mark.django_db
def test_editar_un_registro_en_modo_manual_retorna_409(
    auth_client,
    municipalidad,
    po_base_setup,
):
    """
    GIVEN: un registro EDGE creado con `modo_calculo=MANUAL` (subtotal manual).
    WHEN:  se intenta recalcularlo por tarifa.
    THEN:  409 explícito — una liquidación manual no es recalculable por tarifa
           (si no, el motor leería porcentajes NULL y reventaría con un 500).

    El guard vive en el servicio de PATCH, no en el orquestador del registro
    legacy: es una garantía del FLUJO DE EDICIÓN, que es justo lo que este
    archivo cubre.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=1000.00,
        expediente="EXP-EDGE-MANUAL-001",
    )
    create_response = auth_client.post(
        "/liquidaciones/edificaciones/edge",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )

    liquidacion_id = create_response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(valor_declarado=500000.00),
    )

    assert response.status_code == 409, (
        f"Expected 409 for a MANUAL record, got {response.status_code}: {response.content}"
    )
