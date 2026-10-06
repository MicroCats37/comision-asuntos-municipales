"""
Integration tests for PO /relacionada endpoints.

Tests the /relacionada endpoint for PO types (Edificaciones, Taludes, Impacto Vial).
Each PO type /relacionada creates a liquidacion with numero_revision=1 that is
related to an existing liquidacion via Grupo/Miembro.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Fixtures shared via conftest.py: municipalidad, proyecto, ubigeo_distrito, auth_client,
    api_client, create_user, igv_vigente, uit_vigente, tipo_edificacion,
    tarifa_liquidacion_base_edificacion, especialidad_estructuras, especialidad_arquitectura,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    derecho_porcentaje_vigente.
"""
import pytest
import uuid
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones


# ── Local Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    """District ID from conftest ubigeo_distrito."""
    return str(ubigeo_distrito.id)


@pytest.fixture
def valid_tarifa_ids_edif(tarifa_porcentaje_obra_estructuras, especialidad_estructuras):
    """Return IDs of one tarifa as dict with especialidad_id for Edificaciones."""
    return [
        {"id": str(tarifa_porcentaje_obra_estructuras.id), "esp_id": str(especialidad_estructuras.id)},
    ]


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


def _make_payload_edif_primera(municipalidad, valid_distrito_id, valid_tarifa_ids, tipo_tramite=None):
    """Create primera revision payload for Edificaciones.

    Args:
        tipo_tramite: TipoTramiteEdificaciones value (e.g., OBRA_NUEVA, DEMOLICION).
                      Determines the relation_key: EDIFICACION-OBRA, EDIFICACION-DEMOLICION, etc.
                      Different tipo_tramite → different relacion_key → same group can have both.
    """
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-EDIF-001",
            "observacion": "Test relacionada edificaciones",
            "proyecto": {
                "denominacion": "Proyecto Relacionada Test",
                "nombre_propietario": "Propietario Relacionada SAC",
                "direccion": "Av. Relacionada 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789021",
                    "razon_social": "Propietario Relacionada SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Relacionada",
                "dni": "12345679",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.relacionada@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[0]["id"], "especialidad_id": valid_tarifa_ids[0]["esp_id"]},
            ],
            **({} if tipo_tramite is None else {"tipo_tramite": tipo_tramite}),
        },
    }


def _make_payload_edif_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids, previa_id, tipo_tramite=None):
    """Create relacionada payload for Edificaciones.

    Args:
        tipo_tramite: TipoTramiteEdificaciones value (e.g., OBRA_NUEVA, DEMOLICION).
                      Different tipo_tramite → different relacion_key → can coexist with
                      another member that has the same numero_revision=1 in the same group.
    """
    return {
        "liquidacion_previa_id": str(previa_id),
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-EDIF-002",
            "observacion": "Test relacionada edificaciones 2",
            "proyecto": {
                "denominacion": "Proyecto Relacionada Test 2",
                "nombre_propietario": "Propietario Relacionada 2 SAC",
                "direccion": "Av. Relacionada 456, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789022",
                    "razon_social": "Propietario Relacionada 2 SAC",
                },
            },
            "contacto": {
                "nombres": "Maria",
                "apellidos": "Relacionada",
                "dni": "12345680",
                "cargo": "Gerente",
                "telefono": "123456780",
                "celular": "987654320",
                "email": "maria.relacionada@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[0]["id"], "especialidad_id": valid_tarifa_ids[0]["esp_id"]},
            ],
            **({} if tipo_tramite is None else {"tipo_tramite": tipo_tramite}),
        },
    }


def _make_payload_taludes_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes):
    """Create primera revision payload for Taludes."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-TAL-001",
            "observacion": "Test relacionada taludes",
            "proyecto": {
                "denominacion": "Proyecto Relacionada Taludes Test",
                "nombre_propietario": "Propietario Taludes SAC",
                "direccion": "Av. Taludes 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789031",
                    "razon_social": "Propietario Taludes SAC",
                },
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


def _make_payload_taludes_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes, previa_id):
    """Create relacionada payload for Taludes."""
    return {
        "liquidacion_previa_id": str(previa_id),
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-TAL-002",
            "observacion": "Test relacionada taludes 2",
            "proyecto": {
                "denominacion": "Proyecto Relacionada Taludes Test 2",
                "nombre_propietario": "Propietario Taludes 2 SAC",
                "direccion": "Av. Taludes 456, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789032",
                    "razon_social": "Propietario Taludes 2 SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids_taludes[0]["id"], "especialidad_id": valid_tarifa_ids_taludes[0]["esp_id"]},
            ],
        },
    }


def _make_payload_iv_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_iv):
    """Create primera revision payload for Impacto Vial."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-IV-001",
            "observacion": "Test relacionada impacto vial",
            "proyecto": {
                "denominacion": "Proyecto Relacionada IV Test",
                "nombre_propietario": "Propietario IV SAC",
                "direccion": "Av. IV 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789041",
                    "razon_social": "Propietario IV SAC",
                },
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


def _make_payload_iv_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_iv, previa_id):
    """Create relacionada payload for Impacto Vial."""
    return {
        "liquidacion_previa_id": str(previa_id),
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-REL-IV-002",
            "observacion": "Test relacionada impacto vial 2",
            "proyecto": {
                "denominacion": "Proyecto Relacionada IV Test 2",
                "nombre_propietario": "Propietario IV 2 SAC",
                "direccion": "Av. IV 456, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789042",
                    "razon_social": "Propietario IV 2 SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids_iv[0]["id"], "especialidad_id": valid_tarifa_ids_iv[0]["esp_id"]},
            ],
        },
    }


# ── Helper to create primera revision ──────────────────────────────────────

def crear_primera_revision_edif(auth_client, payload):
    """Helper to create Edificaciones primera revision and return response data."""
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


def crear_primera_revision_taludes(auth_client, payload):
    """Helper to create Taludes primera revision and return response data."""
    response = auth_client.post(
        "/liquidaciones/taludes/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


def crear_primera_revision_iv(auth_client, payload):
    """Helper to create Impacto Vial primera revision and return response data."""
    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


# ── Edificaciones Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_edif_relacionada_crea_liquidacion_numero_revision_1(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_edif,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Edificaciones liquidacion with numero_revision=1
    WHEN: /relacionada is called with valid payload (different tipo_tramite)
    THEN: creates new liquidacion with numero_revision=1
    """
    # Create primera liquidacion (OBRA_NUEVA)
    primera_payload = _make_payload_edif_primera(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif,
        tipo_tramite="OBRA_NUEVA",
    )
    primera = crear_primera_revision_edif(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada (DEMOLICION — different tipo_tramite → different relation_key)
    relacionada_payload = _make_payload_edif_relacionada(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(primera_id),
        tipo_tramite="DEMOLICION",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 200, f"Relacionada failed: {response.content}"
    data = response.json()["data"]

    # Assert numero_revision is 1
    assert data["liquidacion_general"]["numero_revision"] == 1
    assert data["liquidacion_general"]["id"] != primera_id


@pytest.mark.django_db
def test_edif_relacionada_crea_grupo_con_dos_miembros_diferente_tipo_tramite(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_edif,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Edificaciones liquidacion (OBRA_NUEVA, numero_revision=1)
    WHEN: /relacionada is called with a DIFFERENT tipo_tramite (DEMOLICION)
    THEN: creates relation group with both liquidaciones as members
          with different relacion_keys (EDIFICACION-OBRA vs EDIFICACION-DEMOLICION),
          both having numero_revision=1.

    The constraint unique(grupo, relacion_key, numero_revision) allows this because
    the two members have different relacion_keys.
    """
    # Create primera liquidacion with OBRA_NUEVA → relacion_key = "EDIFICACION-OBRA"
    primera_payload = _make_payload_edif_primera(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif,
        tipo_tramite="OBRA_NUEVA",
    )
    primera = crear_primera_revision_edif(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada with DEMOLICION → relacion_key = "EDIFICACION-DEMOLICION"
    # This is different from OBRA, so the constraint allows both in the same group
    relacionada_payload = _make_payload_edif_relacionada(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(primera_id),
        tipo_tramite="DEMOLICION",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 200, f"Relacionada failed: {response.content}"
    data = response.json()["data"]
    relacionada_id = data["liquidacion_general"]["id"]

    # Both liquidaciones should be in the same group
    grupos = LiquidacionRelacionGrupo.objects.filter(
        miembros__liquidacion_id=primera_id
    )
    assert grupos.exists(), "Primera liquidacion should have a group"

    grupo = grupos.first()
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo=grupo)

    # Should have exactly 2 members
    assert miembros.count() == 2, f"Expected 2 members, got {miembros.count()}"

    # Both liquidaciones should be in the group
    miembros_liquidacion_ids = list(miembros.values_list("liquidacion_id", flat=True))
    assert uuid.UUID(primera_id) in miembros_liquidacion_ids
    assert uuid.UUID(relacionada_id) in miembros_liquidacion_ids

    # All members should have numero_revision=1
    for miembro in miembros:
        assert miembro.numero_revision == 1

    # Members should have DIFFERENT relacion_keys
    relacion_keys = {m.relacion_key for m in miembros}
    assert generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA) in relacion_keys
    assert generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.DEMOLICION) in relacion_keys
    assert len(relacion_keys) == 2, f"Expected 2 different relation_keys, got {relacion_keys}"


@pytest.mark.django_db
def test_edif_relacionada_previa_no_existe_devuelve_404(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_edif,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: a payload with non-existent liquidacion_previa_id
    WHEN: /relacionada is called
    THEN: returns 404
    """
    fake_id = str(uuid.uuid4())
    payload = _make_payload_edif_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(fake_id))

    response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=payload,
    )
    assert response.status_code == 404


# ── Taludes Tests ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_taludes_relacionada_crea_liquidacion_numero_revision_1(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_taludes,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Taludes liquidacion with numero_revision=1
    WHEN: /relacionada is called with the same fixed relation key (TALUDES)
    THEN: returns 409 because TALUDES REV1 already exists in the group
    """
    # Create primera liquidacion
    primera_payload = _make_payload_taludes_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_revision_taludes(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada
    relacionada_payload = _make_payload_taludes_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes, uuid.UUID(primera_id))
    response = auth_client.post(
        "/liquidaciones/taludes/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 409, (
        f"Expected 409 Conflict for duplicate TALUDES REV1, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_taludes_relacionada_duplicado_no_agrega_segundo_miembro(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_taludes,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Taludes liquidacion with numero_revision=1
    WHEN: /relacionada is called with another TALUDES REV1
    THEN: keeps the group unchanged because unique(grupo, relacion_key, numero_revision)
          does not allow two TALUDES REV1 members in the same group
    """
    # Create primera liquidacion
    primera_payload = _make_payload_taludes_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes)
    primera = crear_primera_revision_taludes(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada
    relacionada_payload = _make_payload_taludes_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_taludes, uuid.UUID(primera_id))
    response = auth_client.post(
        "/liquidaciones/taludes/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 409, (
        f"Expected 409 Conflict for duplicate TALUDES REV1, got {response.status_code}: {response.content}"
    )

    # Both liquidaciones should be in the same group
    grupos = LiquidacionRelacionGrupo.objects.filter(
        miembros__liquidacion_id=primera_id
    )
    assert grupos.exists(), "Primera liquidacion should have a group"

    grupo = grupos.first()
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo=grupo)

    # Should still have only the original member
    assert miembros.count() == 1, f"Expected 1 member, got {miembros.count()}"

    # Only the original liquidacion should be in the group
    miembros_liquidacion_ids = list(miembros.values_list("liquidacion_id", flat=True))
    assert uuid.UUID(primera_id) in miembros_liquidacion_ids

    # All members should have numero_revision=1
    for miembro in miembros:
        assert miembro.numero_revision == 1

    # Relacion key should be TALUDES
    for miembro in miembros:
        assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.TALUDES)


# ── Impacto Vial Tests ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_iv_relacionada_crea_liquidacion_numero_revision_1(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_iv,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Impacto Vial liquidacion with numero_revision=1
    WHEN: /relacionada is called with the same fixed relation key (IMPACTO_VIAL)
    THEN: returns 409 because IMPACTO_VIAL REV1 already exists in the group
    """
    # Create primera liquidacion
    primera_payload = _make_payload_iv_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_revision_iv(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada
    relacionada_payload = _make_payload_iv_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_iv, uuid.UUID(primera_id))
    response = auth_client.post(
        "/liquidaciones/impacto-vial/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 409, (
        f"Expected 409 Conflict for duplicate IMPACTO_VIAL REV1, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_iv_relacionada_duplicado_no_agrega_segundo_miembro(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_iv,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Impacto Vial liquidacion with numero_revision=1
    WHEN: /relacionada is called with another IMPACTO_VIAL REV1
    THEN: keeps the group unchanged because unique(grupo, relacion_key, numero_revision)
          does not allow two IMPACTO_VIAL REV1 members in the same group
    """
    # Create primera liquidacion
    primera_payload = _make_payload_iv_primera(municipalidad, valid_distrito_id, valid_tarifa_ids_iv)
    primera = crear_primera_revision_iv(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada
    relacionada_payload = _make_payload_iv_relacionada(municipalidad, valid_distrito_id, valid_tarifa_ids_iv, uuid.UUID(primera_id))
    response = auth_client.post(
        "/liquidaciones/impacto-vial/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 409, (
        f"Expected 409 Conflict for duplicate IMPACTO_VIAL REV1, got {response.status_code}: {response.content}"
    )

    # Both liquidaciones should be in the same group
    grupos = LiquidacionRelacionGrupo.objects.filter(
        miembros__liquidacion_id=primera_id
    )
    assert grupos.exists(), "Primera liquidacion should have a group"

    grupo = grupos.first()
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo=grupo)

    # Should still have only the original member
    assert miembros.count() == 1, f"Expected 1 member, got {miembros.count()}"

    # Only the original liquidacion should be in the group
    miembros_liquidacion_ids = list(miembros.values_list("liquidacion_id", flat=True))
    assert uuid.UUID(primera_id) in miembros_liquidacion_ids

    # All members should have numero_revision=1
    for miembro in miembros:
        assert miembro.numero_revision == 1

    # Relacion key should be IMPACTO_VIAL
    for miembro in miembros:
        assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.IMPACTO_VIAL)


# ── Backfill Scenario Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_edif_relacionada_backfill_crea_grupo_si_previa_sin_grupo(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_edif,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an Edificaciones liquidacion that was created WITHOUT relation group
           (e.g., legacy or manually created outside the flow)
    WHEN: /relacionada is called
    THEN: creates a new group with BOTH liquidaciones as members
          (backfill scenario: previous liquidacion is added to new group)

    Uses different tipo_tramite (OBRA_NUEVA vs DEMOLICION) to ensure different
    relation_keys so the constraint allows both members in the same group.
    """
    # Create primera liquidacion with OBRA_NUEVA
    primera_payload = _make_payload_edif_primera(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif,
        tipo_tramite="OBRA_NUEVA",
    )
    primera = crear_primera_revision_edif(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Delete the group that was created by primera revision
    # (simulating a liquidacion without a group)
    LiquidacionRelacionMiembro.objects.filter(liquidacion_id=primera_id).delete()

    # Create relacionada with DEMOLICION (different relation_key)
    relacionada_payload = _make_payload_edif_relacionada(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(primera_id),
        tipo_tramite="DEMOLICION",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 200, f"Relacionada failed: {response.content}"
    data = response.json()["data"]
    relacionada_id = data["liquidacion_general"]["id"]

    # Both should now be in the same group
    grupos = LiquidacionRelacionGrupo.objects.filter(
        miembros__liquidacion_id=primera_id
    )
    assert grupos.exists(), "Should have a group after backfill"

    grupo = grupos.first()
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo=grupo)

    # Should have exactly 2 members after backfill
    assert miembros.count() == 2, f"Expected 2 members after backfill, got {miembros.count()}"

    # Both liquidaciones should be in the group
    miembros_liquidacion_ids = list(miembros.values_list("liquidacion_id", flat=True))
    assert uuid.UUID(primera_id) in miembros_liquidacion_ids
    assert uuid.UUID(relacionada_id) in miembros_liquidacion_ids


# ── Duplicate Constraint Tests ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_edif_relacionada_mismo_tipo_tramite_rechazado_por_constraint(
    auth_client,
    municipalidad,
    valid_distrito_id,
    valid_tarifa_ids_edif,
    igv_vigente,
    uit_vigente,
    derecho_porcentaje_vigente,
):
    """
    GIVEN: an existing Edificaciones liquidacion (OBRA_NUEVA, numero_revision=1)
           and a related liquidacion also with OBRA_NUEVA + numero_revision=1
    WHEN: /relacionada is called AGAIN with the same tipo_tramite (OBRA_NUEVA)
    THEN: returns 409 Conflict because the constraint
          unique(grupo, relacion_key, numero_revision) is violated
          (EDIFICACION-OBRA + REV1 already exists in the group).

    The constraint allows EDIFICACION-OBRA+REV1 and EDIFICACION-DEMOLICION+REV1
    in the same group (different relacion_key), but NOT two EDIFICACION-OBRA+REV1.
    """
    # Create primera with OBRA_NUEVA → relacion_key = "EDIFICACION-OBRA"
    primera_payload = _make_payload_edif_primera(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif,
        tipo_tramite="OBRA_NUEVA",
    )
    primera = crear_primera_revision_edif(auth_client, primera_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create relacionada with DEMOLICION → relacion_key = "EDIFICACION-DEMOLICION"
    # This succeeds because it's a different relation_key
    relacionada_payload = _make_payload_edif_relacionada(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(primera_id),
        tipo_tramite="DEMOLICION",
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=relacionada_payload,
    )
    assert response.status_code == 200, "Primera relacionada (different tipo_tramite) should succeed"

    # Now try to create ANOTHER relacionada with OBRA_NUEVA
    # This should fail with 409 because:
    #   grupo = same group as primera
    #   relacion_key = "EDIFICACION-OBRA" (same as primera)
    #   numero_revision = 1 (same as primera)
    #   → violates unique(grupo, relacion_key, numero_revision)
    dup_payload = _make_payload_edif_relacionada(
        municipalidad, valid_distrito_id, valid_tarifa_ids_edif, uuid.UUID(primera_id),
        tipo_tramite="OBRA_NUEVA",
    )
    dup_response = auth_client.post(
        "/liquidaciones/edificaciones/relacionada",
        json=dup_payload,
    )
    assert dup_response.status_code == 409, (
        f"Expected 409 Conflict for duplicate slot, got {dup_response.status_code}: {dup_response.content}"
    )
