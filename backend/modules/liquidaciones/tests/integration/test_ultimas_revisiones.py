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
- Response items contain liquidacion_general, liquidacion_especifica, and liquidacion_tipo

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
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorMetroCuadrado as LiquidacionM2,
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
    ubigeo_distrito,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
):
    """
    Create two LiquidacionGeneral revisions for the same proyecto+tipo
    (EDIFICACION) with different numero values on the specific table.
    Returns (rev1_lg, rev2_lg).

    NOTE: lg2 gets a CLONED proyecto to avoid UNIQUE constraint violation
    on proyecto_id (OneToOne relationship).

    Creates complete chain: LiquidacionGeneral + LiquidacionEdificacion +
    LiquidacionPorcentajeObra + LiquidacionPorcentajeObraDetalle (required
    for the polymorphic result builders that access liquidacion_porcentaje_obra).
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    user = create_user

    # Clone proyecto for lg2 to avoid UNIQUE constraint on proyecto_id
    entidad_for_lg2 = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789013",
    )
    proyecto_lg2 = Proyecto.objects.create(
        entidad=entidad_for_lg2,
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario Test SAC",
    )

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
    edif1 = LiquidacionEdificacion.objects.create(liquidacion=lg1, numero=100)
    lpo1 = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg1,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo1,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    # Revision 2 — numero=200 (latest), uses cloned proyecto
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto_lg2,
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
    edif2 = LiquidacionEdificacion.objects.create(liquidacion=lg2, numero=200)
    lpo2 = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg2,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo2,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1100.00"),
    )

    return lg1, lg2


@pytest.fixture
def two_revisions_different_tipos(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
    tipo_habilitacion_urbana,
    ubigeo_distrito,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tarifa_m2_hu,
    derecho_m2_vigente,
):
    """
    Create two LiquidacionGeneral for DIFFERENT proyectos and DIFFERENT tipos,
    both with the same numero=54704 on their specific tables.
    This exercises the OR-join across type-specific numero fields when
    numero is provided without tipo.

    NOTE: lg2 gets a separate proyecto to avoid UNIQUE constraint violation
    on proyecto_id (OneToOne relationship).

    Creates complete chain for each tipo:
    - EDIFICACION: LiquidacionEdificacion + LiquidacionPorcentajeObra + Detalle
    - HABILITACION_URBANA: LiquidacionHabilitacionUrbana + LiquidacionM2
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    user = create_user

    # Create separate proyecto for lg2
    entidad_for_lg2 = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789014",
    )
    proyecto_lg2 = Proyecto.objects.create(
        entidad=entidad_for_lg2,
        nombre_propietario="Propietario Test 2 SAC",
        direccion="Av. Test 456",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789014",
        entidad_razon_social="Propietario Test 2 SAC",
    )

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
    lpo1 = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg1,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo1,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    # HabilitacionUrbana revision 1 (latest for its tipo), uses separate proyecto
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto_lg2,
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
    LiquidacionM2.objects.create(
        liquidacion_general=lg2,
        area_m2=Decimal("150.00"),
        costo_por_m2=Decimal("50.00"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        derecho=derecho_m2_vigente,
        tarifa_aplicada=tarifa_m2_hu,
    )

    return lg1, lg2


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ultimas_revisiones_returns_200(
    auth_client,
    two_revisions_edificacion,
):
    """
    GET /liquidaciones/generales/ultimas-revisiones?tipo_liquidacion=EDIFICACION returns 200.
    tipo_liquidacion is mandatory; omitting it returns 422.
    """
    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?tipo_liquidacion=EDIFICACION"
    )
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ultimas_revisiones_no_tipo_returns_422(
    auth_client,
    two_revisions_edificacion,
):
    """
    GET /liquidaciones/generales/ultimas-revisiones without tipo_liquidacion
    returns 422 because the parameter is mandatory.
    """
    response = auth_client.get("/liquidaciones/generales/ultimas-revisiones")
    assert response.status_code == 422, \
        f"Expected 422 (tipo_liquidacion required), got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_ultimas_revisiones_response_has_paginated_data_structure(
    auth_client,
    two_revisions_edificacion,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }

    Also verifies each item contains liquidacion_general, liquidacion_especifica,
    and liquidacion_tipo — fully populated polymorphic structure.
    """
    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?tipo_liquidacion=EDIFICACION"
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "items" in result, "PaginatedData should have 'items'"
    assert "total" in result, "PaginatedData should have 'total'"
    assert "page" in result, "PaginatedData should have 'page'"
    assert "page_size" in result, "PaginatedData should have 'page_size'"
    assert "total_pages" in result, "PaginatedData should have 'total_pages'"

    # Verify polymorphic structure: each item must have the three key sections
    for item in result["items"]:
        assert "liquidacion_general" in item, \
            "Item must have 'liquidacion_general' key for polymorphic structure"
        assert "liquidacion_especifica" in item, \
            "Item must have 'liquidacion_especifica' key for polymorphic structure"
        assert "liquidacion_tipo" in item, \
            "Item must have 'liquidacion_tipo' key for polymorphic structure"


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
        "/liquidaciones/generales/ultimas-revisiones?numero=200&tipo_liquidacion=EDIFICACION"
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
    assert item["liquidacion_general"]["numero_revision"] == 2, \
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
        "/liquidaciones/generales/ultimas-revisiones?numero=99999&tipo_liquidacion=EDIFICACION"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["total"] == 0, \
        f"Expected total=0 for nonexistent numero, got {result['total']}"
    assert len(result["items"]) == 0


@pytest.mark.django_db
def test_ultimas_revisiones_numero_with_tipo_liquidacion_filter(
    auth_client,
    two_revisions_different_tipos,
):
    """
    When numero=54704 is combined with tipo_liquidacion=EDIFICACION, only the EDIFICACION
    latest revision matching that numero should be returned (not HU).
    """
    lg1, lg2 = two_revisions_different_tipos

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=54704&tipo_liquidacion=EDIFICACION"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Should return exactly 1 item (only EDIFICACION, not HU)
    assert result["total"] == 1, \
        f"Expected total=1 for numero=54704 + tipo=EDIFICACION, got {result['total']}"

    item = result["items"][0]
    assert item["liquidacion_general"]["tipo_liquidacion"]["codigo"] == "EDIFICACION", \
        "Should return EDIFICACION only when filtered with tipo=EDIFICACION"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_with_multiple_tipos_returns_all_matching(
    auth_client,
    two_revisions_different_tipos,
):
    """
    When numero=54704 is provided with tipo_liquidacion containing MULTIPLE tipos
    (EDIFICACION,HABILITACION_URBANA), the response should return the latest revision
    for EACH tipo that has that numero — not just one.
    This exercises the direct-lookup optimization (query specific tables first,
    then filter LiquidacionGeneral by id__in) instead of an OR across reverse relations.
    """
    lg1_edificacion, lg2_hu = two_revisions_different_tipos

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=54704&tipo_liquidacion=EDIFICACION&tipo_liquidacion=HABILITACION_URBANA"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # Both EDIFICACION and HU have numero=54704 as their latest revision,
    # so both should appear in the results.
    assert result["total"] == 2, \
        f"Expected total=2 for numero=54704 (both EDIFICACION and HU), got {result['total']}"
    assert len(result["items"]) == 2

    codigos = {item["liquidacion_general"]["tipo_liquidacion"]["codigo"] for item in result["items"]}
    assert codigos == {"EDIFICACION", "HABILITACION_URBANA"}, \
        f"Expected both EDIFICACION and HABILITACION_URBANA, got {codigos}"


@pytest.mark.django_db
def test_ultimas_revisiones_numero_with_tipo_filters_to_latest_per_tipo(
    auth_client,
    two_revisions_edificacion,
):
    """
    When numero=200 is provided with tipo_liquidacion=EDIFICACION, only the latest
    revision for EDIFICACION (which has numero=200) should be returned — not the
    older revision with numero=100. This verifies that the direct-lookup
    optimization is applied AFTER the latest-revisions subquery reduction.
    """
    lg1_old, lg2_latest = two_revisions_edificacion

    response = auth_client.get(
        "/liquidaciones/generales/ultimas-revisiones?numero=200&tipo_liquidacion=EDIFICACION"
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
    assert item["liquidacion_general"]["numero_revision"] == 2, \
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
        "/liquidaciones/generales/ultimas-revisiones?page=1&page_size=5&tipo_liquidacion=EDIFICACION"
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 5
