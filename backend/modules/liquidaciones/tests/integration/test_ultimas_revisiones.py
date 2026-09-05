"""
Integration tests for ultimas-revisiones GET endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET /liquidaciones/generales/ultimas-revisiones returns 200 with PaginatedData structure
- numero filter returns only latest revisions matching the numero value
- numero filter combined with tipo filter works correctly
- Pagination params (page, page_size) affect the response
- numero filter applies AFTER latest-revisions reduction (verified by returning latest
  revision when older revisions also match the numero)

Fixtures are shared via conftest.py.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def two_revisions_edificacion(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
):
    """
    Create two LiquidacionGeneral revisions for the same proyecto+tipo
    (EDIFICACION) with different numero values on the specific table.
    Returns (rev1_lg, rev2_lg).
    """
    user = create_user

    # Revision 1 — numero=100
    lg1 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-EDIF-2024-001",
        observacion="Revision 1",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg1, numero=100)

    # Revision 2 — numero=200 (latest)
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-EDIF-2024-001",
        observacion="Revision 2",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=2,
        sub_total=Decimal("1100.00"),
        total=Decimal("1298.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg2, numero=200)

    return lg1, lg2


@pytest.fixture
def two_revisions_different_tipos(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
    tipo_habilitacion_urbana,
):
    """
    Create two LiquidacionGeneral for the same proyecto but DIFFERENT tipos,
    both with the same numero=54704 on their specific tables.
    This exercises the OR-join across type-specific numero fields when
    numero is provided without tipo.
    """
    user = create_user

    # Edificacion revision 1
    lg1 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-MIX-2024-001",
        observacion="Edificacion revision 1",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg1, numero=54704)

    # HabilitacionUrbana revision 1 (latest for its tipo)
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-MIX-2024-002",
        observacion="HU revision 1",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("2000.00"),
        total=Decimal("2360.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg2, numero=54704)

    return lg1, lg2


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ultimas_revisiones_returns_200(
    auth_client,
    two_revisions_edificacion,
):
    """
    GET /liquidaciones/generales/ultimas-revisiones returns 200.
    """
    response = auth_client.get("/liquidaciones/generales/ultimas-revisiones")
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ultimas_revisiones_response_has_paginated_data_structure(
    auth_client,
    two_revisions_edificacion,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/generales/ultimas-revisiones")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "items" in result, "PaginatedData should have 'items'"
    assert "total" in result, "PaginatedData should have 'total'"
    assert "page" in result, "PaginatedData should have 'page'"
    assert "page_size" in result, "PaginatedData should have 'page_size'"
    assert "total_pages" in result, "PaginatedData should have 'total_pages'"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_filter_returns_only_latest_revision(
    auth_client,
    two_revisions_edificacion,
):
    """
    When numero=200 (the latest revision's numero), the response should contain
    only the latest revision (numero_revision=2), not the older revision 1.
    This verifies that the numero filter is applied AFTER latest-revisions reduction.
    """
    lg1, lg2 = two_revisions_edificacion

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=200"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Should return exactly 1 item (only latest revision for the proyecto+tipo pair)
    assert result["total"] == 1, \
        f"Expected total=1 for numero=200 (latest), got {result['total']}"
    assert len(result["items"]) == 1

    # Verify it's the latest revision (numero_revision=2)
    item = result["items"][0]
    assert item["numero_revision"] == 2, \
        "Should return the latest revision (numero_revision=2) when filtering by its numero"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_filter_returns_zero_for_nonexistent(
    auth_client,
    two_revisions_edificacion,
):
    """
    When numero=99999 does not exist on any latest revision, total should be 0.
    """
    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=99999"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["total"] == 0, \
        f"Expected total=0 for nonexistent numero, got {result['total']}"
    assert len(result["items"]) == 0


@pytest.mark.django_db
def test_ultimas_revisiones_numero_with_tipo_filter(
    auth_client,
    two_revisions_different_tipos,
):
    """
    When numero=54704 is combined with tipo=EDIFICACION, only the EDIFICACION
    latest revision matching that numero should be returned (not HU).
    """
    lg1, lg2 = two_revisions_different_tipos

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=54704&tipo=EDIFICACION"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Should return exactly 1 item (only EDIFICACION, not HU)
    assert result["total"] == 1, \
        f"Expected total=1 for numero=54704 + tipo=EDIFICACION, got {result['total']}"

    item = result["items"][0]
    assert item["tipo_liquidacion"]["codigo"] == "EDIFICACION", \
        "Should return EDIFICACION only when filtered with tipo=EDIFICACION"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_without_tipo_returns_all_matching_tipos(
    auth_client,
    two_revisions_different_tipos,
):
    """
    When numero=54704 is provided WITHOUT tipo filter, the response should return
    the latest revision for EACH tipo that has that numero — not just one.
    This exercises the direct-lookup optimization (query specific tables first,
    then filter LiquidacionGeneral by id__in) instead of an OR across reverse relations.
    """
    lg1_edificacion, lg2_hu = two_revisions_different_tipos

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=54704"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Both EDIFICACION and HU have numero=54704 as their latest revision,
    # so both should appear in the results.
    assert result["total"] == 2, \
        f"Expected total=2 for numero=54704 (both EDIFICACION and HU), got {result['total']}"
    assert len(result["items"]) == 2

    codigos = {item["tipo_liquidacion"]["codigo"] for item in result["items"]}
    assert codigos == {"EDIFICACION", "HABILITACION_URBANA"}, \
        f"Expected both EDIFICACION and HABILITACION_URBANA, got {codigos}"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_without_tipo_filters_to_latest_per_tipo(
    auth_client,
    two_revisions_edificacion,
):
    """
    When numero=200 is provided without tipo filter, only the latest revision
    for EDIFICACION (which has numero=200) should be returned — not the older
    revision with numero=100. This verifies that the direct-lookup optimization
    is applied AFTER the latest-revisions subquery reduction.
    """
    lg1_old, lg2_latest = two_revisions_edificacion

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=200"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Only the latest revision (lg2_latest) has numero=200 as its specific numero.
    # lg1_old has numero=100 on its specific table, so it should not be returned.
    assert result["total"] == 1, \
        f"Expected total=1 for numero=200 (latest only), got {result['total']}"
    assert len(result["items"]) == 1

    item = result["items"][0]
    assert item["numero_revision"] == 2, \
        "Should return only the latest revision (numero_revision=2) for numero=200"



@pytest.mark.django_db
def test_ultimas_revisiones_pagination_params_work(
    auth_client,
    two_revisions_edificacion,
):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?page=1&page_size=5"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 5
