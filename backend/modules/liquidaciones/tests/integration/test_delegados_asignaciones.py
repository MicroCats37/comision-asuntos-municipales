"""
Integration tests for GET /liquidaciones/delegados-asignaciones endpoint.

Tests:
- GET /liquidaciones/delegados-asignaciones returns 200 with PaginatedData structure
- Item has nested liquidacion{proyecto_denominacion, expediente},
  delegado{nombre_completo, cip}, especialidad_revision
- Filter by ?cip= returns only matching items
- Filter by ?liquidacion_id= returns only matching items

Fixtures are shared via ../conftest.py (municipalidad, proyecto, tipo_edificacion, etc.).
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def perfil_ingeniero_asignacion(db):
    """Create a PerfilIngeniero for LiquidacionDelegado test."""
    return PerfilIngeniero.objects.create(
        cip="99999",
        dni="99999999",
        nombres="Carlos",
        apellido_paterno="Ramirez",
        apellido_materno="Lopez",
        correo_personal="carlos.ramirez@test.com",
    )


@pytest.fixture
def perfil_ingeniero_asignacion_2(db):
    """Create a second PerfilIngeniero for filter test."""
    return PerfilIngeniero.objects.create(
        cip="88888",
        dni="88888888",
        nombres="Ana",
        apellido_paterno="Torres",
        apellido_materno="Meza",
        correo_personal="ana.torres@test.com",
    )


@pytest.fixture
def especialidad_revision_asignacion(db):
    """Create an EspecialidadRevision for LiquidacionDelegado test."""
    return EspecialidadRevision.objects.create(
        codigo="T01",
        slug="topografia",
        nombre="Topografía",
    )


@pytest.fixture
def delegado_asignacion(db, perfil_ingeniero_asignacion):
    """Create a Delegado for LiquidacionDelegado test."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_asignacion,
    )


@pytest.fixture
def delegado_asignacion_2(db, perfil_ingeniero_asignacion_2):
    """Create a second Delegado for filter test."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_asignacion_2,
    )


@pytest.fixture
def municipalidad_delegado_asignacion(db, municipalidad, delegado_asignacion, especialidad_revision_asignacion):
    """Delegado-Municipalidad assignment for the first delegado."""
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado_asignacion,
        municipalidad=municipalidad,
        tipo="TITULAR",
        especialidad_revision=especialidad_revision_asignacion,
    )
    DelegadoMunicipalidadPeriodo.objects.create(
        delegado_municipalidad=dm,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )
    return dm


@pytest.fixture
def municipalidad_delegado_asignacion_2(db, municipalidad, delegado_asignacion_2, especialidad_revision_asignacion):
    """Delegado-Municipalidad assignment for the second delegado."""
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado_asignacion_2,
        municipalidad=municipalidad,
        tipo="ALTERNO",
        especialidad_revision=especialidad_revision_asignacion,
    )
    DelegadoMunicipalidadPeriodo.objects.create(
        delegado_municipalidad=dm,
        periodo_inicio=date.today() - timedelta(days=30),
        periodo_fin=None,
    )
    return dm


@pytest.fixture
def liquidacion_asignacion(db, proyecto, municipalidad, tipo_edificacion, create_user):
    """Create a LiquidacionGeneral for LiquidacionDelegado test."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-2026-001",
        sub_total=Decimal("10000.00"),
        total=Decimal("11800.00"),
        usuario_creador=create_user,
    )


@pytest.fixture
def liquidacion_delegado_asignacion(
    db,
    liquidacion_asignacion,
    delegado_asignacion,
    especialidad_revision_asignacion,
):
    """Create a LiquidacionDelegado association for testing."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_asignacion,
        delegado=delegado_asignacion,
        especialidad_revision=especialidad_revision_asignacion,
        periodo="Enero 2026",
        dictamen_revision="APROBADO",
        fecha_presentacion=date(2026, 1, 15),
        fecha_revision=date(2026, 1, 20),
    )


# ── Tests: GET /liquidaciones/delegados-asignaciones ───────────────────────────

@pytest.mark.django_db
def test_delegados_asignaciones_returns_200(
    auth_client,
    liquidacion_delegado_asignacion,
):
    """
    GET /liquidaciones/delegados-asignaciones returns 200.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_delegados_asignaciones_has_paginated_data_structure(
    auth_client,
    liquidacion_delegado_asignacion,
):
    """
    Response has the PaginatedData structure:
    { items: [...], total: N, page: 1, page_size: 10, total_pages: 1 }
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

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
def test_delegados_asignaciones_item_has_nested_liquidacion(
    auth_client,
    liquidacion_delegado_asignacion,
    liquidacion_asignacion,
):
    """
    Each item has nested liquidacion{} with expediente and proyecto_denominacion.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]

    assert len(items) >= 1, "Should have at least 1 item"

    item = items[0]
    assert "liquidacion" in item, "Item should have 'liquidacion' nested object"
    liquidacion = item["liquidacion"]
    assert "expediente" in liquidacion, "liquidacion should have 'expediente'"
    assert "proyecto_denominacion" in liquidacion, "liquidacion should have 'proyecto_denominacion'"
    assert liquidacion["expediente"] == "EXP-2026-001"
    assert liquidacion["proyecto_denominacion"] == "Proyecto Test Edificaciones"


@pytest.mark.django_db
def test_delegados_asignaciones_item_has_nested_delegado(
    auth_client,
    liquidacion_delegado_asignacion,
    perfil_ingeniero_asignacion,
):
    """
    Each item has nested delegado{} with nombre_completo and cip.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]

    assert len(items) >= 1, "Should have at least 1 item"

    item = items[0]
    assert "delegado" in item, "Item should have 'delegado' nested object"
    delegado = item["delegado"]
    assert "nombre_completo" in delegado, "delegado should have 'nombre_completo'"
    assert "cip" in delegado, "delegado should have 'cip'"
    assert delegado["cip"] == "99999"
    assert "Ramirez" in delegado["nombre_completo"]


@pytest.mark.django_db
def test_delegados_asignaciones_item_has_especialidad_revision(
    auth_client,
    liquidacion_delegado_asignacion,
    especialidad_revision_asignacion,
):
    """
    Each item has especialidad_revision{} with id and nombre.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]

    assert len(items) >= 1

    item = items[0]
    assert "especialidad_revision" in item
    esp = item["especialidad_revision"]
    assert "id" in esp
    assert "nombre" in esp
    assert esp["nombre"] == "Topografía"


@pytest.mark.django_db
def test_delegados_asignaciones_filter_by_cip(
    auth_client,
    liquidacion_delegado_asignacion,
    liquidacion_asignacion,
    delegado_asignacion_2,
    municipalidad_delegado_asignacion_2,
    especialidad_revision_asignacion,
):
    """
    GET /liquidaciones/delegados-asignaciones?cip=99999 returns only the matching item.
    """
    # Create a second LiquidacionDelegado with the other delegado
    LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_asignacion,
        delegado=delegado_asignacion_2,
        especialidad_revision=especialidad_revision_asignacion,
    )

    # Filter by cip of the first delegado
    response = auth_client.get("/liquidaciones/delegados-asignaciones?cip=99999")

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]

    assert len(items) == 1, "Should return exactly 1 item matching cip=99999"
    assert items[0]["delegado"]["cip"] == "99999"


@pytest.mark.django_db
def test_delegados_asignaciones_filter_by_liquidacion_id(
    auth_client,
    liquidacion_delegado_asignacion,
    liquidacion_asignacion,
):
    """
    GET /liquidaciones/delegados-asignaciones?liquidacion_id=<id> returns only items for that liquidacion.
    """
    response = auth_client.get(
        f"/liquidaciones/delegados-asignaciones?liquidacion_id={liquidacion_asignacion.id}"
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]

    assert len(items) >= 1, "Should return at least 1 item"
    for item in items:
        assert item["liquidacion_id"] == str(liquidacion_asignacion.id)


@pytest.mark.django_db
def test_delegados_asignaciones_pagination_params_work(
    auth_client,
    liquidacion_delegado_asignacion,
):
    """
    page and page_size params affect the response pagination metadata.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones?page=1&page_size=1")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["page"] == 1
    assert result["page_size"] == 1
    assert result["total"] >= 1
    assert result["total_pages"] >= 1
    assert len(result["items"]) == 1


@pytest.mark.django_db
def test_delegados_asignaciones_empty_returns_empty_items(auth_client, db):
    """
    When no LiquidacionDelegado exist, returns empty items array with total=0.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


@pytest.mark.django_db
def test_delegados_asignaciones_has_required_fields(
    auth_client,
    liquidacion_delegado_asignacion,
):
    """
    Response item has all required top-level fields: id, liquidacion_id, delegado_id,
    especialidad_revision, liquidacion, delegado, periodo, dictamen_revision,
    fecha_presentacion, fecha_revision.
    """
    response = auth_client.get("/liquidaciones/delegados-asignaciones")

    assert response.status_code == 200
    data = response.json()
    item = data["data"]["items"][0]

    assert "id" in item
    assert "liquidacion_id" in item
    assert "delegado_id" in item
    assert "especialidad_revision" in item
    assert "liquidacion" in item
    assert "delegado" in item
    assert "periodo" in item
    assert "dictamen_revision" in item
    assert "fecha_presentacion" in item
    assert "fecha_revision" in item
