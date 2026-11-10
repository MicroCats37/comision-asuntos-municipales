"""
Integration tests for GET /liquidaciones/{liquidacion_id}/delegados-asignaciones.

Nested read endpoint that returns ONLY the assignments (LiquidacionDelegado) of
the requested LiquidacionGeneral, enriched with the RH honorario detail
(DetalleHonorarioDelegado) and the optional linked monthly RH
(ReciboHonorarioDelegadoMensual).

Conventions (contract/TEST_ARCHITECTURE_CONTRACT.md):
- ninja.testing.TestClient through the shared `auth_client` fixture
- @pytest.mark.django_db
- No unittest.mock, no django.test.Client
- Base fixtures (municipalidad, proyecto, tipo_edificacion) come from ../conftest.py
"""
import uuid
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def perfil_ingeniero_detalle(db):
    """PerfilIngeniero for the delegate of the nested detail endpoint."""
    return PerfilIngeniero.objects.create(
        cip="77777",
        dni="77777777",
        nombres="Lucia",
        apellido_paterno="Torres",
        apellido_materno="Rojas",
        correo_personal="lucia.torres@test.com",
    )


@pytest.fixture
def perfil_ingeniero_detalle_2(db):
    """Second PerfilIngeniero (delegate of another liquidation)."""
    return PerfilIngeniero.objects.create(
        cip="66666",
        dni="66666666",
        nombres="Marco",
        apellido_paterno="Alva",
        apellido_materno="Perez",
        correo_personal="marco.alva@test.com",
    )


@pytest.fixture
def especialidad_revision_detalle(db):
    """EspecialidadRevision used by the first assignment."""
    return EspecialidadRevision.objects.create(
        slug="topografia-detalle",
        nombre="Topografía",
    )


@pytest.fixture
def especialidad_revision_detalle_2(db):
    """Second EspecialidadRevision — same delegate, different row."""
    return EspecialidadRevision.objects.create(
        slug="estructuras-detalle",
        nombre="Estructuras",
    )


@pytest.fixture
def delegado_detalle(db, perfil_ingeniero_detalle):
    """Delegado assigned to the liquidation under test."""
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_detalle)


@pytest.fixture
def delegado_detalle_2(db, perfil_ingeniero_detalle_2):
    """Second delegado, used by the "only this liquidation" scenario."""
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_detalle_2)


@pytest.fixture
def operacion_detalle(db, delegado_detalle, municipalidad, especialidad_revision_detalle):
    """DelegadoOperacion — source of the assignment `tipo`."""
    return DelegadoOperacion.objects.create(
        delegado=delegado_detalle,
        municipalidad=municipalidad,
        tipo="TITULAR",
        especialidad_revision=especialidad_revision_detalle,
    )


@pytest.fixture
def liquidacion_detalle(db, proyecto, municipalidad, tipo_edificacion, create_user):
    """LiquidacionGeneral under test."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-2026-DETALLE",
        denominacion_de_proyecto="Proyecto Detalle Asignaciones",
        sub_total=Decimal("10000.00"),
        total=Decimal("11800.00"),
        usuario_creador=create_user,
    )


@pytest.fixture
def liquidacion_detalle_2(db, municipalidad, tipo_edificacion, create_user, ubigeo_distrito):
    """Second LiquidacionGeneral (proyecto is OneToOne → its own proyecto)."""
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20987654321",
    )
    proyecto_2 = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Otro SAC",
        direccion="Av. Otro 456",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20987654321",
        entidad_razon_social="Propietario Otro SAC",
    )
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_2,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-2026-OTRA",
        denominacion_de_proyecto="Proyecto Otra Liquidacion",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        usuario_creador=create_user,
    )


@pytest.fixture
def asignacion_detalle(
    db,
    liquidacion_detalle,
    delegado_detalle,
    especialidad_revision_detalle,
):
    """First assignment (LiquidacionDelegado) of the liquidation under test."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_detalle,
        delegado=delegado_detalle,
        especialidad_revision=especialidad_revision_detalle,
        periodo=2026,
        mes=7,
        dictamen_revision="APROBADO",
        fecha_presentacion=None,
        fecha_revision=None,
    )


@pytest.fixture
def asignacion_detalle_2(
    db,
    liquidacion_detalle,
    delegado_detalle,
    especialidad_revision_detalle_2,
):
    """Second assignment of the SAME delegate (different especialidad_revision)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_detalle,
        delegado=delegado_detalle,
        especialidad_revision=especialidad_revision_detalle_2,
        periodo=2026,
        mes=8,
        dictamen_revision="APROBADO",
    )


@pytest.fixture
def asignacion_otra_liquidacion(
    db,
    liquidacion_detalle_2,
    delegado_detalle_2,
    especialidad_revision_detalle,
):
    """Assignment of ANOTHER liquidation — must never leak into the response."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_detalle_2,
        delegado=delegado_detalle_2,
        especialidad_revision=especialidad_revision_detalle,
    )


@pytest.fixture
def recibo_mensual_detalle(db, delegado_detalle, operacion_detalle):
    """Monthly RH receipt linked to a detail."""
    return ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado_detalle,
        delegado_operacion=operacion_detalle,
        periodo=2026,
        mes=7,
        numero=42,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


@pytest.fixture
def detalle_con_rh_mensual(db, asignacion_detalle, recibo_mensual_detalle):
    """Detail of honorario linked to a monthly RH receipt."""
    return DetalleHonorarioDelegado.objects.create(
        liquidacion_delegado=asignacion_detalle,
        recibo_mensual=recibo_mensual_detalle,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


@pytest.fixture
def detalle_huerfano(db, asignacion_detalle):
    """Detail of honorario WITHOUT a monthly RH receipt (orphan)."""
    return DetalleHonorarioDelegado.objects.create(
        liquidacion_delegado=asignacion_detalle,
        recibo_mensual=None,
        imp_bruto=Decimal("250.00"),
        sub_total=Decimal("250.00"),
        renta_cip=Decimal("62.50"),
        aporte_codemu=Decimal("12.50"),
        fondo_comun=Decimal("25.00"),
        neto_honorario=Decimal("150.00"),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _url(liquidacion_id) -> str:
    return f"/liquidaciones/{liquidacion_id}/delegados-asignaciones"


def _asignaciones(response):
    """Extract the `asignaciones` list from the standard API envelope."""
    return response.json()["data"]["asignaciones"]


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_detalle_asignaciones_devuelve_solo_la_liquidacion_requerida(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    asignacion_otra_liquidacion,
):
    """
    GIVEN: a liquidation A with one assignment and a liquidation B with another.
    WHEN:  GET /liquidaciones/{A}/delegados-asignaciones
    THEN: only the assignment of liquidation A is returned.
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_id"] == str(liquidacion_detalle.id)

    asignaciones = data["asignaciones"]
    assert len(asignaciones) == 1, f"Expected only the assignment of A, got {asignaciones}"
    assert asignaciones[0]["id"] == str(asignacion_detalle.id)
    assert asignaciones[0]["liquidacion_id"] == str(liquidacion_detalle.id)

    ids = {a["id"] for a in asignaciones}
    assert str(asignacion_otra_liquidacion.id) not in ids


@pytest.mark.django_db
def test_detalle_asignaciones_expone_el_id_de_asignacion(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    asignacion_detalle_2,
):
    """
    GIVEN: the same delegate holds two assignment rows (two especialidades).
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: both rows are listed, their ids are distinct and each one reports
          its own especialidad_revision.
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 2

    ids = [a["id"] for a in asignaciones]
    assert len(set(ids)) == 2, f"Assignment ids must be distinct, got {ids}"
    assert str(asignacion_detalle.id) in ids
    assert str(asignacion_detalle_2.id) in ids

    por_id = {a["id"]: a for a in asignaciones}
    assert por_id[str(asignacion_detalle.id)]["especialidad_revision"]["nombre"] == "Topografía"
    assert (
        por_id[str(asignacion_detalle_2.id)]["especialidad_revision"]["nombre"] == "Estructuras"
    )
    assert por_id[str(asignacion_detalle.id)]["delegado_id"] == str(
        asignacion_detalle.delegado_id
    )


@pytest.mark.django_db
def test_detalle_asignaciones_sin_detalle_rh_devuelve_lista_vacia(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
):
    """
    GIVEN: an assignment without a DetalleHonorarioDelegado row.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: the assignment is present and its RH detail list is empty.
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 1
    assert asignaciones[0]["id"] == str(asignacion_detalle.id)
    assert asignaciones[0]["detalle_rh"] == []


@pytest.mark.django_db
def test_detalle_asignaciones_con_rh_mensual_expone_la_cabecera(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    detalle_con_rh_mensual,
    recibo_mensual_detalle,
):
    """
    GIVEN: an assignment whose RH detail links a monthly RH receipt.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: the detail reports the monthly RH header and its frozen totals.
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 1
    detalle_rh = asignaciones[0]["detalle_rh"]
    assert len(detalle_rh) == 1
    assert detalle_rh[0]["id"] == str(detalle_con_rh_mensual.id)
    assert float(detalle_rh[0]["imp_bruto"]) == 1000.00

    recibo = detalle_rh[0]["recibo_mensual"]
    assert recibo is not None, "The detail must expose the linked monthly RH"
    assert recibo["id"] == str(recibo_mensual_detalle.id)
    assert recibo["numero"] == 42
    assert recibo["periodo"] == 2026
    assert recibo["mes"] == 7
    assert recibo["fecha_registro"] is not None
    assert float(recibo["sub_total"]) == 1000.00
    assert float(recibo["renta_cip"]) == 250.00
    assert float(recibo["aporte_codemu"]) == 50.00
    assert float(recibo["fondo_comun"]) == 100.00
    assert float(recibo["neto_honorario"]) == 600.00

    # The monthly RH has no `imp_bruto` — the wrapper must not invent it.
    assert "imp_bruto" not in recibo


@pytest.mark.django_db
def test_detalle_asignaciones_detalle_huerfano_sin_rh_mensual(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    detalle_huerfano,
):
    """
    GIVEN: an assignment whose RH detail has no monthly RH.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: the detail is still listed and its monthly RH field is null.
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 1
    detalle_rh = asignaciones[0]["detalle_rh"]
    assert len(detalle_rh) == 1
    assert detalle_rh[0]["id"] == str(detalle_huerfano.id)
    assert detalle_rh[0]["recibo_mensual"] is None


@pytest.mark.django_db
def test_detalle_asignaciones_reporta_la_metadata_de_la_asignacion(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    operacion_detalle,
):
    """
    GIVEN: an assignment created by the RH workflow.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: it reports numero_rh, creado_por_rh and the operation tipo.
    """
    asignacion_detalle.numero_rh = "RH-000123"
    asignacion_detalle.creado_por_rh = True
    asignacion_detalle.delegado_operacion = operacion_detalle
    asignacion_detalle.save()

    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 1
    asignacion = asignaciones[0]
    assert asignacion["numero_rh"] == "RH-000123"
    assert asignacion["creado_por_rh"] is True
    assert asignacion["tipo"] == "TITULAR"

    # Mutable metadata is exposed as well.
    assert asignacion["periodo"] == 2026
    assert asignacion["mes"] == 7
    assert asignacion["dictamen_revision"] == "APROBADO"


@pytest.mark.django_db
def test_detalle_asignaciones_sin_operacion_reporta_tipo_null(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
):
    """
    GIVEN: an assignment without a DelegadoOperacion.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: `tipo` is null (no crash on the nullable FK).
    """
    response = auth_client.get(_url(liquidacion_detalle.id))

    assert response.status_code == 200, response.content
    asignaciones = _asignaciones(response)

    assert len(asignaciones) == 1
    assert asignaciones[0]["tipo"] is None


@pytest.mark.django_db
def test_detalle_asignaciones_liquidacion_inexistente_devuelve_404(auth_client, db):
    """
    GIVEN: a liquidacion_id that does not exist.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: the response status is 404 and no assignment data is returned.
    """
    response = auth_client.get(_url(uuid.uuid4()))

    assert response.status_code == 404, response.content
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None


@pytest.mark.django_db
def test_detalle_asignaciones_liquidacion_id_no_uuid_devuelve_422(auth_client, db):
    """
    GIVEN: a liquidacion_id that is not a UUID.
    WHEN:  GET /liquidaciones/{id}/delegados-asignaciones
    THEN: the framework rejects it with 422.
    """
    response = auth_client.get(_url("no-es-uuid"))

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_detalle_asignaciones_no_hace_n_plus_one(
    auth_client,
    liquidacion_detalle,
    asignacion_detalle,
    asignacion_detalle_2,
    detalle_con_rh_mensual,
    django_assert_num_queries,
):
    """
    GIVEN: a liquidation with two assignments and one RH detail.
    WHEN:  the assignments are listed with their RH detail.
    THEN: the core query uses a FIXED budget of 3 queries (assignments +
          details + monthly RH receipts) and the endpoint does not scale the
          query count with the number of rows.
    """
    core = DelegadoCoreService()

    with django_assert_num_queries(3):
        asignaciones = core.list_asignaciones_con_detalle_rh(liquidacion_detalle.id)

    assert len(asignaciones) == 2
    # The prefetched relations are already in memory (no extra queries).
    total_detalles = sum(len(a.detalles_honorario.all()) for a in asignaciones)
    assert total_detalles == 1, "The RH detail must be prefetched with the assignments"

    # The endpoint must not add per-row queries: the count is the same with
    # 1 assignment and with 2 assignments.
    url = _url(liquidacion_detalle.id)

    with CaptureQueriesContext(connection) as ctx_2_rows:
        response = auth_client.get(url)
    assert response.status_code == 200, response.content

    asignacion_detalle_2.delete()

    with CaptureQueriesContext(connection) as ctx_1_row:
        response = auth_client.get(url)
    assert response.status_code == 200, response.content

    assert len(ctx_1_row.captured_queries) == len(ctx_2_rows.captured_queries), (
        "The endpoint must not scale its query count with the number of "
        f"assignments: {len(ctx_1_row.captured_queries)} vs "
        f"{len(ctx_2_rows.captured_queries)}"
    )
