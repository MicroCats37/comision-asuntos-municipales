"""
Integration tests for Taludes and Impacto Vial /nueva-revision endpoints.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- Taludes: creating revision 3 from revision 1
- Taludes: creating revision 5 from revision 3
- Taludes: relation key is TALUDES (no tipo_tramite)
- Taludes: contacto preserved from input
- Taludes: MAX_REVISIONES exceeded (REV7 rejected)
- Taludes: previa doesn't exist returns 404
- Impacto Vial: creating revision 3 from revision 1
- Impacto Vial: creating revision 5 from revision 3
- Impacto Vial: relation key is IMPACTO_VIAL (no tipo_tramite)
- Impacto Vial: contacto preserved from input
- Impacto Vial: MAX_REVISIONES exceeded (REV7 rejected)
- Impacto Vial: previa doesn't exist returns 404

Fixtures shared via conftest.py: municipalidad, ubigeo_distrito, auth_client,
    igv_vigente, uit_vigente, tipo_taludes, tipo_impacto_vial,
    tarifa_liquidacion_base_taludes, tarifa_liquidacion_base_iv,
    tarifa_porcentaje_obra_taludes, tarifa_porcentaje_obra_iv,
    especialidad_taludes, especialidad_impacto_vial,
    derecho_porcentaje_vigente.

Local fixtures (defined below): valid_distrito_id, valid_tarifa_ids_taludes,
    valid_tarifa_ids_iv, primera_payload_taludes, primera_payload_iv.
"""
import pytest
import uuid

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)


# ── Local Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    """District ID from conftest ubigeo_distrito."""
    return str(ubigeo_distrito.id)


@pytest.fixture
def valid_tarifa_ids_taludes(tarifa_porcentaje_obra_taludes, especialidad_taludes):
    """Return IDs of one tarifa as dict with especialidad_id for Taludes."""
    return [
        {"id": str(tarifa_porcentaje_obra_taludes.id), "esp_id": str(especialidad_taludes.id)},
    ]


@pytest.fixture
def valid_tarifa_ids_iv(tarifa_porcentaje_obra_iv, especialidad_impacto_vial):
    """Return IDs of one tarifa as dict with especialidad_id for Impacto Vial."""
    return [
        {"id": str(tarifa_porcentaje_obra_iv.id), "esp_id": str(especialidad_impacto_vial.id)},
    ]


# ── Payload Builders ────────────────────────────────────────────────────────────

def _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes):
    """Build primera revision payload for Taludes."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-TAL-NUEVA-001",
            "observacion": "Test Taludes primera revision",
            "proyecto": {
                "denominacion": "Proyecto Taludes NR Test",
                "nombre_propietario": "Propietario Taludes SAC",
                "direccion": "Av. Taludes 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789101",
                    "razon_social": "Propietario Taludes SAC",
                },
            },
            "contacto": {
                "nombres": "Carlos",
                "apellidos": "Taludes",
                "dni": "12345671",
                "cargo": "Ingeniero",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "carlos.taludes@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
            ],
        },
    }


def _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv):
    """Build primera revision payload for Impacto Vial."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-IV-NUEVA-001",
            "observacion": "Test Impacto Vial primera revision",
            "proyecto": {
                "denominacion": "Proyecto IV NR Test",
                "nombre_propietario": "Propietario IV SAC",
                "direccion": "Av. IV 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789111",
                    "razon_social": "Propietario IV SAC",
                },
            },
            "contacto": {
                "nombres": "Pedro",
                "apellidos": "Vial",
                "dni": "12345672",
                "cargo": "Ingeniero",
                "telefono": "123456780",
                "celular": "987654322",
                "email": "pedro.vial@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
            ],
        },
    }


def _nueva_revision_payload(previa_id, expediente, observacion, tarifas, contacto=None):
    """
    Build nueva-revision payload (reduced schema for Taludes/IV).

    Reduced schema contract:
    - liquidacion_previa_id: ID of the previous liquidacion
    - liquidacion_general: expediente + observacion (+ optional contacto)
    - liquidacion_especifica: tarifas only (valor_declarado inherited from previa)
    - NO municipalidad_id, proyecto, or datos in nueva revision
    """
    payload = {
        "liquidacion_previa_id": previa_id,
        "liquidacion_general": {
            "expediente": expediente,
            "observacion": observacion,
        },
        "liquidacion_especifica": {
            "tarifas": tarifas,
        },
    }
    if contacto is not None:
        payload["liquidacion_general"]["contacto"] = contacto
    return payload


# ── Helpers ────────────────────────────────────────────────────────────────────

def crear_primera_taludes(auth_client, payload):
    """Create Taludes primera revision and return response data."""
    response = auth_client.post(
        "/liquidaciones/taludes/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


def crear_primera_iv(auth_client, payload):
    """Create Impacto Vial primera revision and return response data."""
    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


# ── Taludes Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_taludes_crear_revision_3_desde_revision_1(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes: creating revision 3 from revision 1 succeeds.
    numero_revision should be 3.
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_taludes(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(primera_id, "EXP-TAL-NR-002", "Test revision 3", tarifas)

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    data = response.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 3


@pytest.mark.django_db
def test_taludes_crear_revision_5_desde_revision_3(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes: creating revision 5 from revision 3 succeeds.
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_taludes(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-TAL-NR-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200, f"Revision 3 failed: {response_r3.content}"
    revision_3_id = response_r3.json()["data"]["liquidacion_general"]["id"]

    # Create revision 5
    response_r5 = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=_nueva_revision_payload(revision_3_id, "EXP-TAL-NR-003", "Test revision 5", tarifas),
    )

    assert response_r5.status_code == 200, f"Revision 5 failed: {response_r5.content}"
    data = response_r5.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 5


@pytest.mark.django_db
def test_taludes_relacion_key_es_taludes(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes nueva-revision creates a relation group with key TALUDES (no tipo_tramite).
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_taludes(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(primera_id, "EXP-TAL-NR-002", "Test revision 3", tarifas)

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=revision_payload,
    )
    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    revision_3_id = response.json()["data"]["liquidacion_general"]["id"]

    # Verify relation group and members exist
    # relacion_key is on Miembro, not Grupo
    miembros = LiquidacionRelacionMiembro.objects.filter(
        liquidacion_id=primera_id
    )
    assert miembros.exists(), "Primera liquidacion should have a relation member"
    grupo = miembros.first().grupo

    miembros_all = LiquidacionRelacionMiembro.objects.filter(grupo=grupo).order_by("numero_revision")
    assert miembros_all.count() == 2, "Should have 2 members (revision 1 and 3)"
    assert miembros_all[0].numero_revision == 1
    assert miembros_all[1].numero_revision == 3
    # Verify relacion_key is TALUDES for both members
    for m in miembros_all:
        assert m.relacion_key == "TALUDES", f"Expected TALUDES, got {m.relacion_key}"


@pytest.mark.django_db
def test_taludes_contacto_se_preserva(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes: contacto from input is preserved in nueva revision output.
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_taludes(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(
        primera_id, "EXP-TAL-NR-002", "Test revision 3", tarifas,
        contacto={
            "nombres": "Nuevo",
            "apellidos": "Contacto",
            "dni": "11111111",
            "cargo": "Director",
            "telefono": "555555555",
            "celular": "555555556",
            "email": "nuevo.contacto@test.com",
        },
    )

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=revision_payload,
    )
    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    data = response.json()["data"]

    # Contacto from input should be in output
    assert data["liquidacion_general"]["contacto"] is not None
    assert data["liquidacion_general"]["contacto"]["nombres"] == "Nuevo"
    assert data["liquidacion_general"]["contacto"]["email"] == "nuevo.contacto@test.com"


@pytest.mark.django_db
def test_taludes_max_revisiones_excedido(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes: attempting to create revision 7 (beyond MAX_REVISIONES=5) returns 400.
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_taludes(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-TAL-NR-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200
    revision_3_id = response_r3.json()["data"]["liquidacion_general"]["id"]

    # Create revision 5
    response_r5 = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=_nueva_revision_payload(revision_3_id, "EXP-TAL-NR-003", "Test revision 5", tarifas),
    )
    assert response_r5.status_code == 200

    # Try to create revision 7 (should fail)
    revision_7_payload = _nueva_revision_payload(
        response_r5.json()["data"]["liquidacion_general"]["id"],
        "EXP-TAL-NR-004",
        "Test revision 7",
        tarifas,
    )

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=revision_7_payload,
    )

    assert response.status_code == 400, f"Expected 400 for MAX_REVISIONES exceeded, got {response.status_code}"
    error_data = response.json()
    assert "MAX_REVISIONES" in str(error_data.get("error", {}).get("details", {}))


@pytest.mark.django_db
def test_taludes_previa_no_existe_devuelve_404(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes,
    valid_distrito_id, valid_tarifa_ids_taludes
):
    """
    Taludes: creating revision with non-existent previa returns 404.
    """
    payload = _primera_payload_taludes(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    crear_primera_taludes(auth_client, payload)  # Create valid primera to have valid district/municipalidad

    fake_previa_id = str(uuid.uuid4())
    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(fake_previa_id, "EXP-TAL-NR-002", "Test", tarifas)

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 404, f"Expected 404 for non-existent previa, got {response.status_code}"


# ── Impacto Vial Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_iv_crear_revision_3_desde_revision_1(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial: creating revision 3 from revision 1 succeeds.
    numero_revision should be 3.
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_iv(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(primera_id, "EXP-IV-NR-002", "Test revision 3", tarifas)

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    data = response.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 3


@pytest.mark.django_db
def test_iv_crear_revision_5_desde_revision_3(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial: creating revision 5 from revision 3 succeeds.
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_iv(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-IV-NR-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200, f"Revision 3 failed: {response_r3.content}"
    revision_3_id = response_r3.json()["data"]["liquidacion_general"]["id"]

    # Create revision 5
    response_r5 = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=_nueva_revision_payload(revision_3_id, "EXP-IV-NR-003", "Test revision 5", tarifas),
    )

    assert response_r5.status_code == 200, f"Revision 5 failed: {response_r5.content}"
    data = response_r5.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 5


@pytest.mark.django_db
def test_iv_relacion_key_es_impacto_vial(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial nueva-revision creates a relation group with key IMPACTO_VIAL (no tipo_tramite).
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_iv(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(primera_id, "EXP-IV-NR-002", "Test revision 3", tarifas)

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=revision_payload,
    )
    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    revision_3_id = response.json()["data"]["liquidacion_general"]["id"]

    # Verify relation group and members exist
    # relacion_key is on Miembro, not Grupo
    miembros = LiquidacionRelacionMiembro.objects.filter(
        liquidacion_id=primera_id
    )
    assert miembros.exists(), "Primera liquidacion should have a relation member"
    grupo = miembros.first().grupo

    miembros_all = LiquidacionRelacionMiembro.objects.filter(grupo=grupo).order_by("numero_revision")
    assert miembros_all.count() == 2, "Should have 2 members (revision 1 and 3)"
    assert miembros_all[0].numero_revision == 1
    assert miembros_all[1].numero_revision == 3
    # Verify relacion_key is IMPACTO_VIAL for both members
    for m in miembros_all:
        assert m.relacion_key == "IMPACTO_VIAL", f"Expected IMPACTO_VIAL, got {m.relacion_key}"


@pytest.mark.django_db
def test_iv_contacto_se_preserva(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial: contacto from input is preserved in nueva revision output.
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_iv(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(
        primera_id, "EXP-IV-NR-002", "Test revision 3", tarifas,
        contacto={
            "nombres": "Nueva",
            "apellidos": "Contacto",
            "dni": "22222222",
            "cargo": "Gerente",
            "telefono": "666666666",
            "celular": "666666667",
            "email": "nueva.contacto@test.com",
        },
    )

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=revision_payload,
    )
    assert response.status_code == 200, f"Revision 3 failed: {response.content}"
    data = response.json()["data"]

    # Contacto from input should be in output
    assert data["liquidacion_general"]["contacto"] is not None
    assert data["liquidacion_general"]["contacto"]["nombres"] == "Nueva"
    assert data["liquidacion_general"]["contacto"]["email"] == "nueva.contacto@test.com"


@pytest.mark.django_db
def test_iv_max_revisiones_excedido(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial: attempting to create revision 7 (beyond MAX_REVISIONES=5) returns 400.
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_iv(auth_client, payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-IV-NR-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200
    revision_3_id = response_r3.json()["data"]["liquidacion_general"]["id"]

    # Create revision 5
    response_r5 = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=_nueva_revision_payload(revision_3_id, "EXP-IV-NR-003", "Test revision 5", tarifas),
    )
    assert response_r5.status_code == 200

    # Try to create revision 7 (should fail)
    revision_7_payload = _nueva_revision_payload(
        response_r5.json()["data"]["liquidacion_general"]["id"],
        "EXP-IV-NR-004",
        "Test revision 7",
        tarifas,
    )

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=revision_7_payload,
    )

    assert response.status_code == 400, f"Expected 400 for MAX_REVISIONES exceeded, got {response.status_code}"
    error_data = response.json()
    assert "MAX_REVISIONES" in str(error_data.get("error", {}).get("details", {}))


@pytest.mark.django_db
def test_iv_previa_no_existe_devuelve_404(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial,
    valid_distrito_id, valid_tarifa_ids_iv
):
    """
    Impacto Vial: creating revision with non-existent previa returns 404.
    """
    payload = _primera_payload_iv(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    crear_primera_iv(auth_client, payload)  # Create valid primera to have valid district/municipalidad

    fake_previa_id = str(uuid.uuid4())
    tarifas = [
        {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
    ]
    revision_payload = _nueva_revision_payload(fake_previa_id, "EXP-IV-NR-002", "Test", tarifas)

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 404, f"Expected 404 for non-existent previa, got {response.status_code}"
