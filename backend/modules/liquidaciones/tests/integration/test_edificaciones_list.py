"""
Integration tests for Edificaciones GET / list endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- GET / returns 200 with PaginatedData structure
- Pagination params (page, page_size)
- Response contains LiquidacionEdificacionesOutput items
- Empty list returns empty items array

Fixtures are shared via conftest.py (ubigeo, municipalidad, auth, tarifas, etc.).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_edificacion_created(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    Create a persisted LiquidacionGeneral + LiquidacionEdificacion + LiquidacionPorcentajeObra
    for testing the list endpoint.

    Note: igv_id and uit_id are passed as UUID strings (igv_vigente.id, uit_vigente.id)
    because the presenter (present_list) uses str(lg.igv_id) expecting a UUID string,
    not the IGV object's __str__ representation.
    """
    user = create_user

    # Create LiquidacionGeneral
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-EDIF-2024-001",
        observacion="Test liquidation",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    # Create LiquidacionEdificacion (identity)
    edif = LiquidacionEdificacion.objects.create(
        liquidacion=lg,
        numero=1,
    )

    # Create LiquidacionPorcentajeObra
    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    # Create LiquidacionPorcentajeObraDetalle
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_endpoint_returns_200(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    GET /liquidaciones/edificaciones/ returns 200.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_list_response_has_paginated_data_structure(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

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
def test_list_response_contains_liquidacion_edificaciones_output(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    Each item in items has the LiquidacionEdificacionesOutput structure:
    { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert len(result["items"]) >= 1, "Should have at least 1 item"

    item = result["items"][0]
    assert "liquidacion_general" in item, \
        "Item should have 'liquidacion_general'"
    assert "liquidacion_especifica" in item, \
        "Item should have 'liquidacion_especifica'"
    assert "liquidacion_tipo" in item, \
        "Item should have 'liquidacion_tipo'"


@pytest.mark.django_db
def test_list_pagination_params_work(auth_client, liquidacion_edificacion_created):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/liquidaciones/edificaciones/?page=1&page_size=5")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 5


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "expected_total"),
    [
        ("documento=20456789012", 1),
        ("documento=00000000", 0),
        ("expediente=EDIF-2024", 1),
        ("expediente=NO-EXISTE", 0),
    ],
)
def test_list_filters_by_general_liquidation_fields(
    auth_client,
    liquidacion_edificacion_created,
    query,
    expected_total,
):
    response = auth_client.get(f"/liquidaciones/edificaciones/?{query}")

    assert response.status_code == 200
    assert response.json()["data"]["total"] == expected_total


@pytest.mark.django_db
def test_list_empty_returns_empty_items(auth_client, db):
    """
    When no liquidaciones exist, returns empty items array with total=0.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


@pytest.mark.django_db
def test_list_liquidacion_general_has_expected_fields(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    liquidacion_general wrapper has expected fields.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lg = item["liquidacion_general"]

    assert "id" in lg
    assert "municipalidad" in lg
    assert "usuario_creador" in lg
    assert "fecha_registro" in lg
    assert "expediente" in lg
    assert "numero_revision" in lg
    assert "sub_total" in lg
    assert "total" in lg
    assert "proyecto" in lg


@pytest.mark.django_db
def test_list_liquidacion_especifica_has_identity_fields(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    liquidacion_especifica wrapper has id + numero (identity wrapper).
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    le = item["liquidacion_especifica"]

    assert "id" in le
    assert "numero" in le
    assert "valor_declarado" not in le, \
        "liquidacion_especifica should NOT have valor_declarado"


@pytest.mark.django_db
def test_list_liquidacion_tipo_has_calculation_fields(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    liquidacion_tipo wrapper has calculation fields: valor_declarado, detalles, etc.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert "id" in lt
    assert "valor_declarado" in lt
    assert "porcentaje_liquidacion" in lt
    assert "detalles" in lt


@pytest.mark.django_db
def test_list_detalles_have_required_fields(
    auth_client,
    liquidacion_edificacion_created,
):
    """
    Each detalle in liquidacion_tipo.detalles has required fields.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]
    lt = item["liquidacion_tipo"]

    assert len(lt["detalles"]) >= 1, "Should have at least 1 detalle"

    detalle = lt["detalles"][0]
    assert "id" in detalle
    assert "tarifa_aplicada_id" in detalle
    assert "especialidad_id" in detalle
    assert "porcentaje_aplicado" in detalle
    assert "subtotal" in detalle


# ── Sibling liquidaciones (same revision) ─────────────────────────────────────

@pytest.fixture
def liquidacion_edificacion_hermano_rev3(
    db,
    municipalidad,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
    ubigeo_distrito,
):
    """
    A SECOND Edificaciones liquidacion at revision 3, on its own proyecto.

    Together with `liquidacion_edificacion_created` (revision 1) it forms two
    sibling liquidaciones of the same tipo. The revision number is an editable
    label, so several liquidaciones may share it — the listing must admit them
    all instead of collapsing them into one canonical record.
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    user = create_user

    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789077",
    )
    proyecto_hermano = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Hermano SAC",
        direccion="Av. Hermano 789, Lima",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789077",
        entidad_razon_social="Propietario Hermano SAC",
    )

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto_hermano,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-EDIF-REV3-HERMANO",
        observacion="Liquidacion hermana en revision 3",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=2)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


@pytest.mark.django_db
def test_list_filtrado_por_numero_revision_es_exacto(
    auth_client,
    liquidacion_edificacion_created,
    liquidacion_edificacion_hermano_rev3,
):
    """
    The `numero_revisiones` filter is exact: revision 3 does not match revision 1.
    """
    response = auth_client.get("/liquidaciones/edificaciones/?numero_revisiones=3")

    assert response.status_code == 200
    result = response.json()["data"]

    assert result["total"] == 1, \
        f"Expected only the revision-3 liquidacion, got total={result['total']}"

    item = result["items"][0]
    assert item["liquidacion_general"]["numero_revision"] == 3


@pytest.mark.django_db
def test_list_admite_hermanos_con_la_misma_revision(
    auth_client,
    liquidacion_edificacion_created,
    liquidacion_edificacion_hermano_rev3,
):
    """
    Several liquidaciones may share the same revision number: the standard
    paginated per-type listing admits all of them (no canonical record is picked).
    """
    # Move the first liquidacion to revision 3 as well → two siblings at rev 3.
    liquidacion_edificacion_created.numero_revision = 3
    liquidacion_edificacion_created.save(update_fields=["numero_revision"])

    response = auth_client.get("/liquidaciones/edificaciones/?numero_revisiones=3")

    assert response.status_code == 200
    result = response.json()["data"]

    assert result["total"] == 2, \
        f"Expected both siblings at revision 3, got total={result['total']}"
    assert len(result["items"]) == 2

    assert {item["liquidacion_general"]["numero_revision"] for item in result["items"]} == {3}


@pytest.mark.django_db
def test_list_paginado_conserva_el_total_con_hermanos(
    auth_client,
    liquidacion_edificacion_created,
    liquidacion_edificacion_hermano_rev3,
):
    """
    The paginated per-type listing keeps every sibling and reports the real total
    (it does not collapse them into a single "latest" record).
    """
    liquidacion_edificacion_created.numero_revision = 3
    liquidacion_edificacion_created.save(update_fields=["numero_revision"])

    response = auth_client.get("/liquidaciones/edificaciones/?page=1&page_size=10")

    assert response.status_code == 200
    result = response.json()["data"]

    assert result["total"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert len(result["items"]) == 2


@pytest.mark.django_db
def test_list_devuelve_todas_las_revisiones_sin_reduccion_canonica(
    auth_client,
    liquidacion_edificacion_created,
    liquidacion_edificacion_hermano_rev3,
):
    """
    The per-type listing returns EVERY revision of the tipo: the retired
    canonical-latest machinery used to hide the lower revisions, and the standard
    listing must not do that.
    """
    response = auth_client.get("/liquidaciones/edificaciones/")

    assert response.status_code == 200
    result = response.json()["data"]

    assert result["total"] == 2, \
        f"Expected both revisions in the listing, got total={result['total']}"

    revisiones = {
        item["liquidacion_general"]["numero_revision"]
        for item in result["items"]
    }
    assert revisiones == {1, 3}, \
        f"Expected revisions 1 and 3 (no canonical reduction), got {revisiones}"

