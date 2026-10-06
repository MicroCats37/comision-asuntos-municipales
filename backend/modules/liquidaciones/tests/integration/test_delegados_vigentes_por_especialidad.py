"""
Integration tests for EspecialidadesRevision and Delegados Vigentes Por Especialidad endpoints.

Tests cover:
- GET /liquidaciones/especialidades-revision returns all EspecialidadRevision records
- GET /liquidaciones/especialidades-revision returns ordered by nombre
- GET /liquidaciones/delegados/vigentes-por-especialidad returns delegates filtered by specialty
- GET /liquidaciones/delegados/vigentes-por-especialidad returns empty when no delegates
- GET /liquidaciones/delegados/vigentes-por-especialidad returns 404 for invalid especialidad_revision_id
- GET /liquidaciones/delegados/vigentes-por-especialidad returns 404 for nonexistent especialidad_revision_id
- Existing GET /liquidaciones/delegados/vigentes still works (regression)
"""
import pytest
from datetime import date, timedelta
import uuid

from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def especialidad_civil(db):
    """Create EspecialidadRevision Civil."""
    return EspecialidadRevision.objects.create(
        slug="civil",
        nombre="Ingeniería Civil",
    )


@pytest.fixture
def especialidad_sanitaria(db):
    """Create EspecialidadRevision Sanitaria."""
    return EspecialidadRevision.objects.create(
        slug="sanitaria",
        nombre="Ingeniería Sanitaria",
    )


@pytest.fixture
def especialidad_electrica(db):
    """Create EspecialidadRevision Eléctrica/Mecánica."""
    return EspecialidadRevision.objects.create(
        slug="electrica-mecanica",
        nombre="Ingeniería Eléctrica y Mecánica",
    )


@pytest.fixture
def perfil_delegado_civil(db):
    """Create PerfilIngeniero for civil delegate."""
    return PerfilIngeniero.objects.create(
        cip="12345",
        dni="76543210",
        nombres="Juan",
        apellido_paterno="Perez",
        apellido_materno="Garcia",
        correo_personal="juan.perez@test.com",
    )


@pytest.fixture
def perfil_delegado_sanitaria(db):
    """Create PerfilIngeniero for sanitaria delegate."""
    return PerfilIngeniero.objects.create(
        cip="54321",
        dni="87654321",
        nombres="Maria",
        apellido_paterno="Lopez",
        apellido_materno="Rodriguez",
        correo_personal="maria.lopez@test.com",
    )


@pytest.fixture
def delegado_civil(db, perfil_delegado_civil):
    """Create Delegado for civil."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_delegado_civil,
    )


@pytest.fixture
def delegado_sanitaria(db, perfil_delegado_sanitaria):
    """Create Delegado for sanitaria."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_delegado_sanitaria,
    )


@pytest.fixture
def operacion_civil(db, delegado_civil, municipalidad, especialidad_civil):
    """Create DelegadoOperacion for civil delegate."""
    return DelegadoOperacion.objects.create(
        delegado=delegado_civil,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_civil,
        tipo="TITULAR",
    )


@pytest.fixture
def operacion_sanitaria(db, delegado_sanitaria, municipalidad, especialidad_sanitaria):
    """Create DelegadoOperacion for sanitaria delegate."""
    return DelegadoOperacion.objects.create(
        delegado=delegado_sanitaria,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_sanitaria,
        tipo="ALTERNO",
    )


@pytest.fixture
def periodo_vigente_civil(db, operacion_civil):
    """Create vigente periodo for civil operacion."""
    return DelegadoOperacionPeriodo.objects.create(
        delegado_municipalidad=operacion_civil,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )


@pytest.fixture
def periodo_vigente_sanitaria(db, operacion_sanitaria):
    """Create vigente periodo for sanitaria operacion."""
    return DelegadoOperacionPeriodo.objects.create(
        delegado_municipalidad=operacion_sanitaria,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )


# ── Tests: GET /liquidaciones/especialidades-revision ─────────────────────────────────

@pytest.mark.django_db
def test_especialidades_revision_returns_200(auth_client):
    """
    GET /liquidaciones/especialidades-revision returns 200.
    """
    response = auth_client.get("/liquidaciones/especialidades-revision")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_especialidades_revision_returns_all_especialidades(
    auth_client,
    especialidad_civil,
    especialidad_sanitaria,
    especialidad_electrica,
):
    """
    Returns all EspecialidadRevision records.
    """
    response = auth_client.get("/liquidaciones/especialidades-revision")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert "especialidades" in result
    assert len(result["especialidades"]) == 3

    nombres = {e["nombre"] for e in result["especialidades"]}
    assert "Ingeniería Civil" in nombres
    assert "Ingeniería Sanitaria" in nombres
    assert "Ingeniería Eléctrica y Mecánica" in nombres


@pytest.mark.django_db
def test_especialidades_revision_returns_ordered_by_nombre(
    auth_client,
    especialidad_electrica,
    especialidad_civil,
    especialidad_sanitaria,
):
    """
    Returns especialidades ordered alphabetically by nombre.
    """
    response = auth_client.get("/liquidaciones/especialidades-revision")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    nombres = [e["nombre"] for e in result["especialidades"]]
    assert nombres == sorted(nombres)


@pytest.mark.django_db
def test_especialidades_revision_has_id_and_nombre(
    auth_client,
    especialidad_civil,
):
    """
    Each especialidad has id and nombre fields.
    """
    response = auth_client.get("/liquidaciones/especialidades-revision")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    esp = result["especialidades"][0]
    assert "id" in esp
    assert "nombre" in esp
    assert esp["nombre"] == "Ingeniería Civil"


# ── Tests: GET /liquidaciones/delegados/vigentes-por-especialidad ─────────────────────────────────

@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_200(
    auth_client,
    especialidad_civil,
    operacion_civil,
    periodo_vigente_civil,
):
    """
    GET /liquidaciones/delegados/vigentes-por-especialidad returns 200.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_delegados_filtered_by_especialidad(
    auth_client,
    especialidad_civil,
    especialidad_sanitaria,
    operacion_civil,
    operacion_sanitaria,
    periodo_vigente_civil,
    periodo_vigente_sanitaria,
):
    """
    Returns only delegates with the requested especialidad_revision.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert "delegados" in result
    assert len(result["delegados"]) == 1
    assert result["delegados"][0]["nombre_completo"] == "Juan Perez Garcia"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_empty_when_no_delegates(
    auth_client,
    especialidad_electrica,
):
    """
    Returns empty list when no delegates have the requested especialidad.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_electrica.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["delegados"] == []


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_422_for_invalid_uuid(auth_client):
    """
    Returns 422 for invalid UUID format (Pydantic validation error).
    """
    response = auth_client.get(
        "/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id=not-a-uuid"
    )

    assert response.status_code == 422, \
        f"Expected 422, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_404_for_nonexistent_especialidad(
    auth_client,
):
    """
    Returns 404 when EspecialidadRevision does not exist.
    """
    fake_uuid = uuid.uuid4()
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={fake_uuid}"
    )

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_correct_fields(
    auth_client,
    especialidad_civil,
    operacion_civil,
    periodo_vigente_civil,
):
    """
    Response has the expected fields: id, nombre_completo, cip, tipo, especialidad.
    tipo is empty string when querying by Delegado (semantically not meaningful
    at the Delegado level for this endpoint).
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["delegados"]) == 1
    delegado_item = result["delegados"][0]

    assert "id" in delegado_item
    assert "nombre_completo" in delegado_item
    assert delegado_item["nombre_completo"] == "Juan Perez Garcia"
    assert "cip" in delegado_item
    assert delegado_item["cip"] == "12345"
    assert "tipo" in delegado_item
    # tipo is empty string when deduplicating by Delegado
    assert delegado_item["tipo"] == ""
    assert "especialidad" in delegado_item
    assert delegado_item["especialidad"]["nombre"] == "Ingeniería Civil"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_filters_by_fecha(
    auth_client,
    especialidad_civil,
    operacion_civil,
    periodo_vigente_civil,
):
    """
    When fecha is in the past (before periodo_inicio), returns empty.
    """
    yesterday = (date.today() - timedelta(days=60)).isoformat()
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}&fecha={yesterday}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # The periodo started 30 days ago, so 60 days ago it didn't exist yet
    assert result["delegados"] == []


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_default_fecha_is_today(
    auth_client,
    especialidad_civil,
    operacion_civil,
    periodo_vigente_civil,
):
    """
    When fecha is omitted, defaults to today and returns vigentes.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["delegados"]) == 1


# ── Deduplication tests: same Delegado with multiple operations/periods appears once ─────────────────────────────────

@pytest.fixture
def perfil_delegado_multi(db):
    """Create PerfilIngeniero for multi-operation delegate."""
    return PerfilIngeniero.objects.create(
        cip="99999",
        dni="11223344",
        nombres="Carlos",
        apellido_paterno="Ruiz",
        apellido_materno="Martinez",
        correo_personal="carlos.ruiz@test.com",
    )


@pytest.fixture
def delegado_multi(db, perfil_delegado_multi):
    """Create Delegado for multi-operation tests."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_delegado_multi,
    )


@pytest.fixture
def municipalidad_2(db, ubigeo_distrito):
    """Create a second municipalidad for multi-operation tests."""
    from modules.entidades.domain.models.municipalidad import Municipalidad
    return Municipalidad.objects.create(
        codigo="MUN002",
        nombre="Municipalidad Test 2",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def operacion_multi_1(db, delegado_multi, municipalidad, especialidad_civil):
    """Create first DelegadoOperacion for the multi-operation delegate."""
    return DelegadoOperacion.objects.create(
        delegado=delegado_multi,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_civil,
        tipo="TITULAR",
    )


@pytest.fixture
def operacion_multi_2(db, delegado_multi, municipalidad_2, especialidad_civil):
    """Create second DelegadoOperacion (different municipalidad) for same delegate."""
    return DelegadoOperacion.objects.create(
        delegado=delegado_multi,
        municipalidad=municipalidad_2,
        especialidad_revision=especialidad_civil,
        tipo="ALTERNO",
    )


@pytest.fixture
def periodo_vigente_multi_1(db, operacion_multi_1):
    """Create vigente periodo for first operation."""
    return DelegadoOperacionPeriodo.objects.create(
        delegado_municipalidad=operacion_multi_1,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )


@pytest.fixture
def periodo_vigente_multi_2(db, operacion_multi_2):
    """Create vigente periodo for second operation."""
    return DelegadoOperacionPeriodo.objects.create(
        delegado_municipalidad=operacion_multi_2,
        periodo_inicio=date.today() - timedelta(days=15),
        periodo_fin=None,
    )


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_same_delegado_appears_once(
    auth_client,
    especialidad_civil,
    operacion_multi_1,
    operacion_multi_2,
    periodo_vigente_multi_1,
    periodo_vigente_multi_2,
):
    """
    Given a Delegado with multiple active DelegadoOperacion entries for the same
    EspecialidadRevision (different municipalidades), the endpoint returns
    exactly ONE entry for that Delegado (deduplicated by Delegado.id).
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert "delegados" in result
    # Should be exactly 1, not 2 (not one per operation)
    assert len(result["delegados"]) == 1
    assert result["delegados"][0]["nombre_completo"] == "Carlos Ruiz Martinez"


@pytest.mark.django_db
def test_delegados_vigentes_por_especialidad_returns_delegado_id_not_operacion_id(
    auth_client,
    especialidad_civil,
    operacion_multi_1,
    operacion_multi_2,
    periodo_vigente_multi_1,
    periodo_vigente_multi_2,
    delegado_multi,
):
    """
    The returned id is Delegado.id, not DelegadoOperacion.id.
    This ensures the wizard uses the correct ID for LiquidacionDelegado creation.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id={especialidad_civil.id}"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    returned_id = result["delegados"][0]["id"]
    # Must be Delegado.id, not any DelegadoOperacion.id
    assert returned_id == str(delegado_multi.id)
    # Sanity check: it's not the operation id
    assert returned_id != str(operacion_multi_1.id)
    assert returned_id != str(operacion_multi_2.id)


# ── Regression: Existing /delegados/vigentes still works ─────────────────────────────────

@pytest.mark.django_db
def test_delegados_vigentes_still_works_regression(
    auth_client,
    municipalidad,
    tipo_edificacion,
    especialidad_civil,
    operacion_civil,
    periodo_vigente_civil,
):
    """
    GET /liquidaciones/delegados/vigentes (original endpoint) still works.
    This is a regression test to ensure we didn't break existing functionality.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}&tipo_liquidacion=EDIFICACION"
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    assert "data" in data
    assert "delegados" in data["data"]
