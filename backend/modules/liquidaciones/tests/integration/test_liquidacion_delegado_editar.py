"""
Integration tests for the exact-assignment edit of the delegated batch.

PATCH /liquidaciones/{liquidacion_id}/delegados — the `update` branch extended
with the optional `liquidacion_delegado_id` discriminator:

- When the discriminator is present the target is that exact row
  (LiquidacionDelegado), not the delegate.
- Existence (404) and ownership (400) of the assignment are validated before
  anything is written.
- Field semantics are explicit: an absent field keeps the persisted value, an
  explicit `null` clears it.
- Range validation (`mes`, `periodo`, `dictamen_revision`, `numero_rh`) lives in
  the presentation schema → 422 before the database is touched.
- The legacy payload (only `delegado_id`) keeps working unchanged.
- PROTECTED ASSIGNMENT: an assignment whose RH detail links a monthly RH
  (ReciboHonorarioDelegadoMensual) CANNOT be edited → 409 before any write,
  with the assignment, the RH detail, the monthly RH and the liquidation left
  intact. Same safety rule as the guarded removal.

Conventions (contract/TEST_ARCHITECTURE_CONTRACT.md):
- ninja.testing.TestClient through the shared `auth_client` fixture
- @pytest.mark.django_db
- No unittest.mock, no django.test.Client
- Base fixtures (municipalidad, proyecto, tipo_edificacion) come from ../conftest.py
"""
import uuid
from decimal import Decimal

import pytest

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.liquidaciones.domain.constants import (
    DictamenRevision,
    EstadoLiquidacion,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def perfil_ingeniero_editar(db):
    """PerfilIngeniero of the delegate under test."""
    return PerfilIngeniero.objects.create(
        cip="55555",
        dni="55555555",
        nombres="Ana",
        apellido_paterno="Rios",
        apellido_materno="Vega",
        correo_personal="ana.rios@test.com",
    )


@pytest.fixture
def especialidad_revision_editar(db):
    """EspecialidadRevision of the first assignment."""
    return EspecialidadRevision.objects.create(
        slug="topografia-editar",
        nombre="Topografía",
    )


@pytest.fixture
def especialidad_revision_editar_2(db):
    """Second EspecialidadRevision — same delegate, different assignment row."""
    return EspecialidadRevision.objects.create(
        slug="estructuras-editar",
        nombre="Estructuras",
    )


@pytest.fixture
def delegado_editar(db, perfil_ingeniero_editar):
    """Delegado assigned to the liquidation under test."""
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_editar)


@pytest.fixture
def liquidacion_editar(db, proyecto, municipalidad, tipo_edificacion, create_user):
    """LiquidacionGeneral under test."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-2026-EDITAR",
        denominacion_de_proyecto="Proyecto Editar Asignaciones",
        sub_total=Decimal("10000.00"),
        total=Decimal("11800.00"),
        usuario_creador=create_user,
    )


@pytest.fixture
def liquidacion_editar_2(db, municipalidad, tipo_edificacion, create_user, ubigeo_distrito):
    """Second LiquidacionGeneral (proyecto is OneToOne → its own proyecto)."""
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20111222333",
    )
    proyecto_2 = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Editar SAC",
        direccion="Av. Editar 789",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20111222333",
        entidad_razon_social="Propietario Editar SAC",
    )
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_2,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-2026-EDITAR-OTRA",
        denominacion_de_proyecto="Proyecto Editar Otra Liquidacion",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        usuario_creador=create_user,
    )


@pytest.fixture
def asignacion_editar(
    db,
    liquidacion_editar,
    delegado_editar,
    especialidad_revision_editar,
):
    """First assignment (LiquidacionDelegado) of the liquidation under test."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_editar,
        delegado=delegado_editar,
        especialidad_revision=especialidad_revision_editar,
        periodo=2026,
        mes=7,
        dictamen_revision=DictamenRevision.CONFORME,
    )


@pytest.fixture
def asignacion_editar_2(
    db,
    liquidacion_editar,
    delegado_editar,
    especialidad_revision_editar_2,
):
    """Second assignment of the SAME delegate (different especialidad_revision)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_editar,
        delegado=delegado_editar,
        especialidad_revision=especialidad_revision_editar_2,
        periodo=2026,
        mes=8,
        dictamen_revision=DictamenRevision.CONFORME,
    )


@pytest.fixture
def asignacion_otra_liquidacion(
    db,
    liquidacion_editar_2,
    delegado_editar,
    especialidad_revision_editar,
):
    """Assignment of ANOTHER liquidation — must never be modified from A."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_editar_2,
        delegado=delegado_editar,
        especialidad_revision=especialidad_revision_editar,
        periodo=2025,
        mes=3,
        dictamen_revision=DictamenRevision.PENDIENTE,
    )


@pytest.fixture
def recibo_mensual_editar(db, delegado_editar):
    """Monthly RH receipt of the delegate — it protects its assignment."""
    return ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado_editar,
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
def detalle_con_rh_mensual_editar(db, asignacion_editar, recibo_mensual_editar):
    """RH detail of the assignment LINKED to the monthly RH receipt."""
    return DetalleHonorarioDelegado.objects.create(
        liquidacion_delegado=asignacion_editar,
        recibo_mensual=recibo_mensual_editar,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


@pytest.fixture
def detalle_huerfano_editar(db, asignacion_editar):
    """RH detail of the assignment WITHOUT a monthly RH receipt (orphan)."""
    return DetalleHonorarioDelegado.objects.create(
        liquidacion_delegado=asignacion_editar,
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
    return f"/liquidaciones/{liquidacion_id}/delegados"


def _patch(auth_client, liquidacion_id, payload):
    """PATCH the delegated batch endpoint."""
    return auth_client.patch(_url(liquidacion_id), json=payload)


def _updated(response):
    """Extract the `updated` list from the standard API envelope."""
    return response.json()["data"]["updated"]


def _refrescar(asignacion):
    """Re-read the assignment from the database."""
    asignacion.refresh_from_db()
    return asignacion


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_update_por_liquidacion_delegado_id_actualiza_esa_asignacion(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
    asignacion_editar_2,
):
    """
    GIVEN: the same delegate holds two assignment rows.
    WHEN:  an update item carries the id of the second row.
    THEN: only the second row is modified and the first keeps its metadata.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar_2.id), "mes": 11}]},
    )

    assert response.status_code == 200, response.content

    actualizadas = _updated(response)
    assert len(actualizadas) == 1
    assert actualizadas[0]["id"] == str(asignacion_editar_2.id)
    assert actualizadas[0]["mes"] == 11

    assert _refrescar(asignacion_editar_2).mes == 11
    assert _refrescar(asignacion_editar).mes == 7, (
        "The assignment that was not targeted must keep its persisted metadata"
    )


@pytest.mark.django_db
def test_update_por_liquidacion_delegado_id_es_independiente_por_fila(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
    asignacion_editar_2,
):
    """
    GIVEN: the same delegate holds two assignment rows with different `mes`.
    WHEN:  the `mes` of the first row is updated with its own assignment id.
    THEN: the first row reports the new `mes` and the second keeps its original.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar.id), "mes": 3}]},
    )

    assert response.status_code == 200, response.content

    actualizadas = _updated(response)
    assert len(actualizadas) == 1
    assert actualizadas[0]["id"] == str(asignacion_editar.id)
    assert actualizadas[0]["mes"] == 3

    assert _refrescar(asignacion_editar).mes == 3
    assert _refrescar(asignacion_editar_2).mes == 8


@pytest.mark.django_db
def test_update_con_liquidacion_delegado_id_de_otra_liquidacion_devuelve_400(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
    asignacion_otra_liquidacion,
):
    """
    GIVEN: an assignment that belongs to liquidation B.
    AND:    a request to update liquidation A carrying that assignment id.
    WHEN:   the batch payload is sent.
    THEN:   the response status is 400 and no row was modified.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_otra_liquidacion.id), "mes": 9}]},
    )

    assert response.status_code == 400, response.content
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None

    assert _refrescar(asignacion_otra_liquidacion).mes == 3, (
        "The assignment of the other liquidation must not be modified"
    )
    assert _refrescar(asignacion_editar).mes == 7


@pytest.mark.django_db
def test_update_con_liquidacion_delegado_id_inexistente_devuelve_404(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: a liquidacion_delegado_id that does not exist.
    WHEN:  the batch payload is sent.
    THEN:  the response status is 404 and no row was modified.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(uuid.uuid4()), "mes": 9}]},
    )

    assert response.status_code == 404, response.content
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None

    assert _refrescar(asignacion_editar).mes == 7


@pytest.mark.django_db
def test_update_con_mes_fuera_de_rango_devuelve_422(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment of a liquidation.
    WHEN:  an update item sets `mes` to 13.
    THEN:  the response status is 422 and the persisted `mes` is unchanged.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar.id), "mes": 13}]},
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "mes" in (body["error"]["details"] or {}), (
        "The invalid field must be identified in the validation details"
    )

    assert _refrescar(asignacion_editar).mes == 7


@pytest.mark.django_db
def test_update_con_periodo_fuera_de_rango_devuelve_422(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment of a liquidation.
    WHEN:  an update item sets `periodo` outside 1900-2100.
    THEN:  the response status is 422 and the persisted `periodo` is unchanged.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar.id), "periodo": 1899}]},
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "periodo" in (body["error"]["details"] or {})

    assert _refrescar(asignacion_editar).periodo == 2026


@pytest.mark.django_db
def test_update_con_dictamen_revision_invalido_devuelve_422(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment of a liquidation.
    WHEN:  an update item sets `dictamen_revision` to a value outside the
           allowed choices.
    THEN:  the response status is 422 and the persisted value is unchanged.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {
            "update": [
                {
                    "liquidacion_delegado_id": str(asignacion_editar.id),
                    "dictamen_revision": "NO_EXISTE",
                }
            ]
        },
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "dictamen_revision" in (body["error"]["details"] or {})

    assert _refrescar(asignacion_editar).dictamen_revision == DictamenRevision.CONFORME


@pytest.mark.django_db
def test_update_con_numero_rh_demasiado_largo_devuelve_422(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment of a liquidation.
    WHEN:  an update item sets `numero_rh` to more than 50 characters.
    THEN:  the response status is 422 and nothing was persisted.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {
            "update": [
                {
                    "liquidacion_delegado_id": str(asignacion_editar.id),
                    "numero_rh": "RH-" + ("X" * 60),
                }
            ]
        },
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "numero_rh" in (body["error"]["details"] or {})

    assert _refrescar(asignacion_editar).numero_rh is None


@pytest.mark.django_db
def test_update_con_null_explicito_limpia_el_campo(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment whose `dictamen_revision` is set.
    WHEN:  an update item sets `dictamen_revision` to null explicitly.
    THEN:  the persisted `dictamen_revision` is null.
    """
    assert asignacion_editar.dictamen_revision == DictamenRevision.CONFORME

    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {
            "update": [
                {
                    "liquidacion_delegado_id": str(asignacion_editar.id),
                    "dictamen_revision": None,
                }
            ]
        },
    )

    assert response.status_code == 200, response.content
    assert _refrescar(asignacion_editar).dictamen_revision is None


@pytest.mark.django_db
def test_update_con_campo_ausente_conserva_el_valor(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an assignment whose `dictamen_revision` is set.
    WHEN:  an update item sends only the `mes` field.
    THEN:  the persisted `dictamen_revision` is unchanged.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar.id), "mes": 5}]},
    )

    assert response.status_code == 200, response.content

    refrescada = _refrescar(asignacion_editar)
    assert refrescada.mes == 5
    assert refrescada.dictamen_revision == DictamenRevision.CONFORME, (
        "An absent field must keep its persisted value"
    )
    assert refrescada.periodo == 2026


@pytest.mark.django_db
def test_update_legacy_sigue_funcionando(
    auth_client,
    liquidacion_editar,
    delegado_editar,
    asignacion_editar,
):
    """
    GIVEN: a liquidation with a delegate assignment.
    WHEN:  an update item that carries only `delegado_id` is sent.
    THEN:  the request is accepted and the update is applied through the legacy
           resolution.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"delegado_id": str(delegado_editar.id), "mes": 6}]},
    )

    assert response.status_code == 200, response.content

    actualizadas = _updated(response)
    assert len(actualizadas) == 1
    assert actualizadas[0]["mes"] == 6

    assert _refrescar(asignacion_editar).mes == 6


@pytest.mark.django_db
def test_update_persiste_el_numero_rh_de_la_asignacion(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: a liquidation with a delegate assignment.
    WHEN:  an update item sets `numero_rh` to a valid value.
    THEN:  the assignment persists that `numero_rh`.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {
            "update": [
                {
                    "liquidacion_delegado_id": str(asignacion_editar.id),
                    "numero_rh": "RH-000999",
                }
            ]
        },
    )

    assert response.status_code == 200, response.content
    assert _refrescar(asignacion_editar).numero_rh == "RH-000999"


@pytest.mark.django_db
def test_update_sin_discriminador_ni_delegado_id_devuelve_422(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
):
    """
    GIVEN: an update item without `liquidacion_delegado_id` and without
           `delegado_id`.
    WHEN:  the batch payload is sent.
    THEN:  the response status is 422 and no row was modified.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"mes": 4}]},
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"

    details = body["error"]["details"] or {}
    assert details, "The validation error must identify the offending item"
    assert any("liquidacion_delegado_id" in str(msg) for msg in details.values()), (
        f"The error must explain the missing discriminator, got {details}"
    )

    assert _refrescar(asignacion_editar).mes == 7


# ── Asignación protegida por un RH mensual (409 antes de cualquier escritura) ──


@pytest.mark.django_db
def test_update_con_rh_mensual_enlazado_devuelve_409_y_no_escribe_nada(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
    detalle_con_rh_mensual_editar,
    recibo_mensual_editar,
):
    """
    GIVEN: an assignment whose RH detail links a monthly RH receipt.
    WHEN:  an update item targets that exact assignment.
    THEN:  the response status is 409 and NOTHING is written: the assignment
           keeps its metadata, the RH detail and the monthly RH survive, and
           the liquidation is untouched.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {
            "update": [
                {
                    "liquidacion_delegado_id": str(asignacion_editar.id),
                    "mes": 9,
                    "numero_rh": "RH-000123",
                }
            ]
        },
    )

    assert response.status_code == 409, response.content
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "CONFLICT"
    # El mensaje identifica al delegado por su CIP, nunca por el UUID crudo.
    assert "55555" in body["error"]["message"]
    assert str(asignacion_editar.delegado_id) not in body["error"]["message"]

    # La asignación conserva TODOS sus campos.
    refrescada = _refrescar(asignacion_editar)
    assert refrescada.mes == 7
    assert refrescada.periodo == 2026
    assert refrescada.dictamen_revision == DictamenRevision.CONFORME
    assert refrescada.numero_rh is None

    # El detalle de honorario sigue existiendo y enlazado a SU recibo mensual.
    detalle = DetalleHonorarioDelegado.objects.get(
        id=detalle_con_rh_mensual_editar.id
    )
    assert detalle.recibo_mensual_id == recibo_mensual_editar.id

    # El RH mensual no se elimina ni se recalcula.
    rh = ReciboHonorarioDelegadoMensual.objects.get(id=recibo_mensual_editar.id)
    assert rh.sub_total == Decimal("1000.00")
    assert rh.renta_cip == Decimal("250.00")
    assert rh.aporte_codemu == Decimal("50.00")
    assert rh.fondo_comun == Decimal("100.00")
    assert rh.neto_honorario == Decimal("600.00")

    # La liquidación sobrevive intacta.
    liquidacion = LiquidacionGeneral.objects.get(id=liquidacion_editar.id)
    assert liquidacion.total == Decimal("11800.00")


@pytest.mark.django_db
def test_update_sin_rh_mensual_enlazado_se_aplica(
    auth_client,
    liquidacion_editar,
    asignacion_editar,
    detalle_huerfano_editar,
):
    """
    GIVEN: an assignment whose RH detail has NO monthly RH receipt (orphan).
    WHEN:  an update item targets that exact assignment.
    THEN:  the update is applied (200): the guard only blocks assignments
           protected by a linked monthly RH.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"liquidacion_delegado_id": str(asignacion_editar.id), "mes": 9}]},
    )

    assert response.status_code == 200, response.content
    assert _refrescar(asignacion_editar).mes == 9


@pytest.mark.django_db
def test_update_legacy_con_rh_mensual_enlazado_devuelve_409(
    auth_client,
    liquidacion_editar,
    delegado_editar,
    asignacion_editar,
    detalle_con_rh_mensual_editar,
):
    """
    GIVEN: an assignment protected by a monthly RH receipt.
    WHEN:  a LEGACY update item (only `delegado_id`) targets the delegate.
    THEN:  the response status is 409 and the assignment keeps its metadata:
           the guard cannot be bypassed by omitting the discriminator.
    """
    response = _patch(
        auth_client,
        liquidacion_editar.id,
        {"update": [{"delegado_id": str(delegado_editar.id), "mes": 6}]},
    )

    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "CONFLICT"

    assert _refrescar(asignacion_editar).mes == 7, (
        "The protected assignment must not be modified by the legacy path"
    )
