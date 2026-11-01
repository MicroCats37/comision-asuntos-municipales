"""
Integration tests for the INITIAL STATE and VISIBILITY of legacy records
(Phase 3, task 3.2 — "PENDIENTE/normal visibility").

Requirement (MODIFIED — Initial state and visibility): legacy records MUST
use the existing `PENDIENTE` default and MUST appear in normal listings with
the existing Legacy badge. No new state management is introduced.

What this file proves:
- a legacy record is created in `PENDIENTE` (an EXISTING state — there is no
  special legacy state);
- the legacy record appears in the NORMAL listing of its type, with the
  `legacy=true` flag that drives the existing Legacy badge;
- the same holds for the second engine family (M2), not only for PO.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest

from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_legacy_m2,
    make_payload_legacy_po,
    make_payload_po,
)


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_registro_legacy_se_crea_en_el_estado_pendiente_existente(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un operador registra una liquidación legacy.
    WHEN:  se crea el registro.
    THEN:  el estado es `PENDIENTE` — un estado YA EXISTENTE, no uno especial
           para legacy (la gestión de estados queda fuera de alcance).
    """
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=8301,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        expediente="EXP-ESTADO-LEGACY-001",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=payload,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    lg = response.json()["data"]["liquidacion_general"]
    assert lg["estado"] == EstadoLiquidacion.PENDIENTE
    assert lg["estado"] in EstadoLiquidacion.values


@pytest.mark.django_db
def test_registro_legacy_aparece_en_el_listado_normal_con_el_flag_legacy(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy creado por la ruta tipada.
    WHEN:  se consulta el listado NORMAL del tipo.
    THEN:  el registro aparece en `items` con `legacy=true` (el flag que ya
           alimenta el badge Legacy del frontend) y en estado `PENDIENTE`.
    """
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=8302,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        expediente="EXP-VISIBILIDAD-LEGACY-001",
    )
    create_response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )
    liquidacion_id = create_response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    assert result["total"] >= 1

    item = next(
        i for i in result["items"] if i["liquidacion_general"]["id"] == liquidacion_id
    )
    assert item["liquidacion_general"]["legacy"] is True
    assert item["liquidacion_general"]["estado"] == EstadoLiquidacion.PENDIENTE
    assert item["liquidacion_especifica"]["numero"] == 8302


@pytest.mark.django_db
def test_registro_legacy_aparece_en_el_listado_normal_de_habilitacion_urbana(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy de Habilitación Urbana.
    WHEN:  se consulta el listado NORMAL de Habilitación Urbana.
    THEN:  el registro aparece con `legacy=true` y en estado `PENDIENTE`.
    """
    payload = make_payload_legacy_m2(
        municipalidad.id,
        municipalidad.distrito_id,
        catalogo_legacy_historico["tarifa_m2_habilitacion_urbana"].id,
        numero=8303,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        expediente="EXP-VISIBILIDAD-LEGACY-HU-001",
    )
    create_response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )
    liquidacion_id = create_response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.get("/liquidaciones/habilitacion-urbana/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    item = next(
        i for i in result["items"] if i["liquidacion_general"]["id"] == liquidacion_id
    )
    assert item["liquidacion_general"]["legacy"] is True
    assert item["liquidacion_general"]["estado"] == EstadoLiquidacion.PENDIENTE
    assert item["liquidacion_especifica"]["numero"] == 8303


@pytest.mark.django_db
def test_el_listado_normal_muestra_el_flag_legacy_tambien_en_registros_normales(
    auth_client,
    municipalidad,
    po_base_setup,
):
    """
    GIVEN: un registro NORMAL (no legacy) del mismo tipo.
    WHEN:  se consulta el listado normal.
    THEN:  el registro aparece con `legacy=false` — el flag discrimina los dos
           orígenes sin cambiar el contrato del listado.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-VISIBILIDAD-NORMAL-001",
        valor_declarado=1000000.00,
        tarifas=None,
    )
    create_response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert create_response.status_code == 200, (
        f"Expected 200, got {create_response.status_code}: {create_response.content}"
    )
    liquidacion_id = create_response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    item = next(
        i for i in result["items"] if i["liquidacion_general"]["id"] == liquidacion_id
    )
    assert item["liquidacion_general"]["legacy"] is False
