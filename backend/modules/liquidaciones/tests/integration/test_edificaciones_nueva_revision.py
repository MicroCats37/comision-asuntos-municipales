"""
Integration tests for Edificaciones /nueva-revision endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- Creating revision 3 from revision 1
- Creating revision 5 from revision 3
- The revision number is the one sent by the client (never derived from the previa)
- Duplicate siblings with the same revision number coexist in the same group
- Validation: previa doesn't exist
- Validation: revision number outside the allowed set {1, 3, 5} / MAX_REVISIONES
- Contact upsert: reuse when all fields match
- Contact upsert: create new when fields differ
- The legacy GET /ultima-revision endpoint is gone: no canonical-latest semantics

Fixtures shared via conftest.py: municipalidad, proyecto, ubigeo_distrito, auth_client,
    api_client, create_user, igv_vigente, uit_vigente, tipo_edificacion,
    tarifa_liquidacion_base_edificacion, especialidad_estructuras, especialidad_arquitectura,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, derecho_porcentaje_vigente.

Local fixtures (not in conftest): tarifa_porcentaje_obra_base2 (second base+tarifa for
    explicit mode), valid_distrito_id, valid_tarifa_ids, primera_revision_payload.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.tests.fixtures.http_helpers import status_de_ruta_retirada


# ── Local Fixtures (not in conftest) ────────────────────────────────────────────

@pytest.fixture
def tarifa_porcentaje_obra_base2(db, tipo_edificacion):
    """Second base + TarifaPorcentajeObra for explicit mode test."""
    base2 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base2,
        porcentaje_liquidacion=Decimal("0.0005"),
    )


@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    """District ID from conftest ubigeo_distrito."""
    return str(ubigeo_distrito.id)


@pytest.fixture
def valid_tarifa_ids(tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_base2, especialidad_estructuras, especialidad_arquitectura):
    """Return IDs of two tarifas as dicts with especialidad_id (new contract)."""
    return [
        {"id": str(tarifa_porcentaje_obra_estructuras.id), "esp_id": str(especialidad_estructuras.id)},
        {"id": str(tarifa_porcentaje_obra_base2.id), "esp_id": str(especialidad_arquitectura.id)},
    ]


@pytest.fixture
def primera_revision_payload(valid_tarifa_ids, municipalidad, valid_distrito_id):
    """Payload for creating primera revision (full schema — NOT the reduced nueva-revision schema)."""
    return {
        "numero_revision": 1,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-001",
            "observacion": "Test primera revision",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[0]["id"], "especialidad_id": valid_tarifa_ids[0]["esp_id"]},
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[1]["id"], "especialidad_id": valid_tarifa_ids[1]["esp_id"]},
            ],
        },
    }


def _nueva_revision_payload(
    primera_id,
    expediente,
    observacion,
    tarifas,
    tipo_tramite="OBRA_NUEVA",
    numero_revision=3,
):
    """Reduced payload for /nueva-revision matching LiquidacionEdificacionesNuevaRevisionInput.

    `numero_revision` is the revision chosen by the client; the backend never
    derives it from the previa.
    """
    return {
        "liquidacion_previa_id": primera_id,
        "numero_revision": numero_revision,
        "liquidacion_general": {
            "expediente": expediente,
            "observacion": observacion,
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "tipo_tramite": tipo_tramite,
            "tarifas": tarifas,
        },
    }


# ── Helper to create primera revision ────────────────────────────────────

def crear_primera_revision(auth_client, payload):
    """Helper to create primera revision and return the response data."""
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


# ── Tests ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_revision_3_desde_revision_1(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
    ):
    """
    Creating revision 3 from revision 1 succeeds.
    numero_revision should be 3.
    (liquidacion_raiz y LiquidacionRelacionada fueron removidos en desarrollo.)
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create nueva revision payload (revision 3) — reduced schema
    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]
    revision_3_payload = _nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas)

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_3_payload,
    )

    assert response.status_code == 200, f"Revision 3 failed: {response.content}"

    data = response.json()["data"]
    revision_3_id = data["liquidacion_general"]["id"]
    assert data["liquidacion_general"]["numero_revision"] == 3
    # tipo_tramite is preserved from input through to output
    assert data["liquidacion_tipo"]["tipo_tramite"] == "OBRA_NUEVA"


@pytest.mark.django_db
def test_crear_revision_5_desde_revision_3(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    Creating revision 5 from revision 3 succeeds.
    (liquidacion_raiz y LiquidacionRelacionada fueron removidos en desarrollo.)
    """
    # Create primera revision (revision 1)
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]

    # Create revision 3 — reduced schema
    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200, f"Revision 3 failed: {response_r3.content}"
    revision_3 = response_r3.json()["data"]
    revision_3_id = revision_3["liquidacion_general"]["id"]

    # Create revision 5 — reduced schema
    response_r5 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(
            revision_3_id, "EXP-EDIF-NUEVA-003", "Test revision 5", tarifas, numero_revision=5,
        ),
    )

    assert response_r5.status_code == 200, f"Revision 5 failed: {response_r5.content}"

    data = response_r5.json()["data"]
    revision_5_id = data["liquidacion_general"]["id"]
    assert data["liquidacion_general"]["numero_revision"] == 5
    # tipo_tramite is preserved from input through to output
    assert data["liquidacion_tipo"]["tipo_tramite"] == "OBRA_NUEVA"


@pytest.mark.django_db
def test_tipo_tramite_ampliacion_se_conserva_en_output(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    especialidad_estructuras, especialidad_arquitectura,
    primera_revision_payload
):
    """
    tipo_tramite=AMPLIACION sent in nueva-revision is persisted and returned in output.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
    ]

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(
            primera_id, "EXP-EDIF-AMPLIACION", "Test ampliacion", tarifas,
            tipo_tramite="AMPLIACION",
        ),
    )

    assert response.status_code == 200, f"AMPLIACION revision failed: {response.content}"
    data = response.json()["data"]
    assert data["liquidacion_tipo"]["tipo_tramite"] == "AMPLIACION"


@pytest.mark.django_db
def test_previa_no_existe_devuelve_404(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    Creating revision with non-existent previa returns 404.
    """
    # Create primera revision to have a valid municipalidad/distrito
    primera = crear_primera_revision(auth_client, primera_revision_payload)

    fake_previa_id = str(uuid.uuid4())
    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]
    revision_payload = _nueva_revision_payload(fake_previa_id, "EXP-EDIF-NUEVA-002", "Test", tarifas)
    # Override contacto to None per original test intent
    revision_payload["liquidacion_general"]["contacto"] = None

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 404, f"Expected 404 for non-existent previa, got {response.status_code}"


@pytest.mark.django_db
def test_max_revisiones_excedido_es_rechazado_por_el_contrato(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    A revision number above MAX_REVISIONES=5 is rejected by the input contract.

    The allowed set {1, 3, 5} and the MAX_REVISIONES bound live in the request
    contract, so the payload never reaches the orchestrator.
    """
    # Create revision 1, 3, 5
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200
    revision_3_id = response_r3.json()["data"]["liquidacion_general"]["id"]

    # Create revision 5
    response_r5 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(
            revision_3_id, "EXP-EDIF-NUEVA-003", "Test revision 5", tarifas, numero_revision=5,
        ),
    )
    assert response_r5.status_code == 200

    # Try to create revision 7 (should fail - MAX is 5)
    revision_7_payload = _nueva_revision_payload(
        response_r5.json()["data"]["liquidacion_general"]["id"],
        "EXP-EDIF-NUEVA-004",
        "Test revision 7",
        tarifas,
        numero_revision=7,
    )

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_7_payload,
    )

    assert response.status_code == 422, (
        f"Expected 422 for a revision number above MAX_REVISIONES, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_hermanos_con_misma_revision_coexisten(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    Two revisions with the SAME number created from the same previa coexist.

    The revision number is an editable label, not a uniqueness constraint: there is
    no canonical revision and repeated active revisions are allowed.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
        LiquidacionRelacionMiembro,
    )

    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = uuid.UUID(primera["liquidacion_general"]["id"])

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
    ]

    # First revision 3
    response_1 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-EDIF-HERMANO-1", "Test hermano 1", tarifas),
    )
    assert response_1.status_code == 200, response_1.content
    hermano_1_id = uuid.UUID(response_1.json()["data"]["liquidacion_general"]["id"])

    # Second revision 3 — same slot, same group
    response_2 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-EDIF-HERMANO-2", "Test hermano 2", tarifas),
    )
    assert response_2.status_code == 200, response_2.content
    hermano_2_id = uuid.UUID(response_2.json()["data"]["liquidacion_general"]["id"])

    assert response_2.json()["data"]["liquidacion_general"]["numero_revision"] == 3

    grupo_id = LiquidacionRelacionMiembro.objects.get(liquidacion_id=primera_id).grupo_id
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id)
    assert miembros.count() == 3
    assert hermano_1_id in set(miembros.values_list("liquidacion_id", flat=True))
    assert hermano_2_id in set(miembros.values_list("liquidacion_id", flat=True))
    assert set(miembros.values_list("numero_revision", flat=True)) == {1, 3}


@pytest.mark.django_db
def test_endpoint_ultima_revision_ya_no_existe(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    GET /ultima-revision ya no existe: el endpoint canonico-latest fue retirado.

    El revision number es una etiqueta editable, no una identidad de secuencia —
    ya no hay "una revision canonica por proyecto". El listado paginado por tipo
    es el reemplazo.
    """
    # Create primera revision (the flow still works without the latest endpoint)
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]

    # Create revision 3
    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=_nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas),
    )
    assert response_r3.status_code == 200

    # The canonical-latest endpoint is gone
    status = status_de_ruta_retirada(
        auth_client, "/liquidaciones/edificaciones/ultima-revision"
    )

    assert status in (404, 405), (
        f"Expected the retired endpoint to be unreachable, got {status}"
    )


@pytest.mark.django_db
def test_contacto_upsert_reutiliza_existente(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    When contacto has ALL same fields, it should be reused (not created).
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]
    primera_contacto_id = primera["liquidacion_general"]["contacto"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]

    # Create revision 3 with same contacto fields
    r3_payload = _nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas)

    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]

    # Contacto should be the same
    assert revision_3["liquidacion_general"]["contacto"]["id"] == primera_contacto_id


@pytest.mark.django_db
def test_contacto_upsert_crea_nuevo_si_diferente(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    primera_revision_payload
):
    """
    When contacto has different fields, a new contacto should be created.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]
    primera_contacto_id = primera["liquidacion_general"]["contacto"]["id"]

    tarifas = [
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id), "especialidad_id": str(especialidad_estructuras.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_arquitectura.id), "especialidad_id": str(especialidad_arquitectura.id)},
        {"tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_installaciones.id), "especialidad_id": str(especialidad_installaciones.id)},
    ]

    # Create revision 3 with different contacto
    r3_payload = _nueva_revision_payload(primera_id, "EXP-EDIF-NUEVA-002", "Test revision 3", tarifas)
    r3_payload["liquidacion_general"]["contacto"] = {
        "nombres": "Maria",
        "apellidos": "Garcia",
        "dni": "87654321",
        "cargo": "Directora",
        "telefono": "999888777",
        "celular": "777888999",
        "email": "maria.garcia@test.com",
    }

    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]

    # Contacto should be different (new one)
    assert revision_3["liquidacion_general"]["contacto"]["id"] != primera_contacto_id
    assert revision_3["liquidacion_general"]["contacto"]["nombres"] == "Maria"


@pytest.mark.django_db
def test_endpoint_ultima_revision_con_filtros_ya_no_existe(
    auth_client
):
    """
    GET /ultima-revision with filters ya no existe: el endpoint fue retirado.
    """
    status = status_de_ruta_retirada(
        auth_client,
        "/liquidaciones/edificaciones/ultima-revision?numero_documento=00000000",
    )

    assert status in (404, 405), (
        f"Expected the retired endpoint to be unreachable, got {status}"
    )


@pytest.mark.django_db
def test_tarifas_vacias_devuelve_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    especialidad_estructuras, especialidad_arquitectura,
    primera_revision_payload
):
    """
    Sending tarifas: [] in nueva-revision returns 400.
    Backend schema LiquidacionEspecificaNuevaRevisionIn requires tarifas to be non-empty,
    and the orchestrator validates this explicitly.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Payload with empty tarifas
    empty_tarifas_payload = _nueva_revision_payload(primera_id, "EXP-EDIF-VACIO", "Test tarifas vacias", [])

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=empty_tarifas_payload,
    )

    assert response.status_code == 400, (
        f"Expected 400 for empty tarifas, got {response.status_code}: {response.content}"
    )
    error_data = response.json()
    # Backend returns explicit error in details.non_field_errors
    details = error_data.get("error", {}).get("details", {})
    error_detail = str(details)
    assert "tarifa" in error_detail.lower(), (
        f"Expected tarifas-related error in details, got: {error_data}"
    )
