"""
Integration tests for PATCH /liquidaciones/generales/{liquidacion_id}/comprobante/{comprobante_id}.

Covers the in-place edit of the ACTIVE comprobante:

- 404 when the liquidacion does not exist
- 404 when the comprobante does not exist
- 404 when the comprobante belongs to another liquidacion
- 404 when the liquidacion has no comprobantes at all
- 409 (COMPROBANTE_NO_ACTIVO) when the comprobante is a historical one
- real in-place update: same row, same id, no history growth, exactly one active
- `monto` is preserved (it is not even an input field)
- `motivo_reemplazo` is never touched
- no PAGADA guard (parity with POST /comprobante)
- `numero_revision` is invariant
- standard ApiResponse envelope

Pattern (TEST_ARCHITECTURE_CONTRACT.md): ninja.testing.TestClient via the shared
`auth_client` fixture (JWT), @pytest.mark.django_db, fixtures from the root
conftest.py, NO unittest.mock and NO `unit/` folder.

These tests are DEFINED here; their execution belongs to the `sdd-verify` phase.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.presentation.schemas.liquidacion_general.comprobante_schemas import (
    LiquidacionComprobanteUpdateIn,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _url(liquidacion_id, comprobante_id) -> str:
    """Builds the PATCH url of the comprobante resource."""
    return f"/liquidaciones/generales/{liquidacion_id}/comprobante/{comprobante_id}"


def _payload(**overrides) -> dict:
    """
    Body of the comprobante edition request.

    `monto` is deliberately absent: it is NOT an input field of the PATCH contract.
    """
    payload = {
        "tipo_comprobante": "FACTURA",
        "serie": "F001",
        "numero": "0001-2026",
        "fecha_emision": "2026-11-06",
    }
    payload.update(overrides)
    return payload


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def crear_liquidacion(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
):
    """Factory of base LiquidacionGeneral rows for the edition tests."""
    def _create(
        *,
        proyecto_override=None,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-EDIT-001",
        numero_revision=1,
    ):
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto_override or proyecto,
            municipalidad=municipalidad,
            usuario_creador=create_user,
            expediente=expediente,
            observacion="Test liquidacion para edicion in-place de comprobante",
            estado=estado,
            tipo_liquidacion=tipo_edificacion,
            numero_revision=numero_revision,
            sub_total=Decimal("1000.00"),
            total=Decimal("1180.00"),
            igv_id=igv_vigente,
            uit_id=uit_vigente,
        )

    return _create


@pytest.fixture
def crear_comprobante(db):
    """Factory of LiquidacionComprobante rows for the edition tests."""
    def _create(liquidacion_general, *, activo=True, **kwargs):
        defaults = {
            "tipo_comprobante": "FACTURA",
            "serie": "F001",
            "numero": "0001-2026",
            "fecha_emision": date(2026, 11, 1),
            "monto": Decimal("1500.00"),
            "activo": activo,
        }
        defaults.update(kwargs)
        return LiquidacionComprobante.objects.create(
            liquidacion_general=liquidacion_general,
            **defaults,
        )

    return _create


@pytest.fixture
def segundo_proyecto(db, municipalidad, ubigeo_distrito):
    """A second Proyecto — LiquidacionGeneral.proyecto is a OneToOneField."""
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20999999999",
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Secondary SAC",
        direccion="Av. Secondary 456",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20999999999",
        entidad_razon_social="Propietario Secondary SAC",
    )


@pytest.fixture
def liquidacion_con_comprobante(crear_liquidacion, crear_comprobante):
    """Liquidacion PENDIENTE with a single ACTIVE comprobante (monto 1500.00)."""
    liquidacion = crear_liquidacion(expediente="EXP-EDIT-ACTIVO-001")
    comprobante = crear_comprobante(liquidacion, activo=True)
    return liquidacion, comprobante


@pytest.fixture
def liquidacion_con_historico(crear_liquidacion, crear_comprobante):
    """Liquidacion PENDIENTE with an ACTIVE comprobante plus a historical one."""
    liquidacion = crear_liquidacion(expediente="EXP-EDIT-HISTORICO-001")
    activo = crear_comprobante(liquidacion, activo=True, serie="F001", numero="0001-2026")
    historico = crear_comprobante(
        liquidacion,
        activo=False,
        tipo_comprobante="BOLETA",
        serie="B001",
        numero="0001-2025",
        fecha_emision=date(2025, 11, 1),
        monto=Decimal("1200.00"),
        motivo_reemplazo="Comprobante anterior anulado",
    )
    return liquidacion, activo, historico


@pytest.fixture
def liquidacion_sin_comprobantes(crear_liquidacion):
    """Liquidacion PENDIENTE without any comprobante."""
    return crear_liquidacion(expediente="EXP-EDIT-SIN-COMPROBANTES-001")


@pytest.fixture
def liquidacion_pagada_con_comprobante(crear_liquidacion, crear_comprobante):
    """Liquidacion PAGADA with an ACTIVE comprobante (parity check with POST)."""
    liquidacion = crear_liquidacion(
        estado=EstadoLiquidacion.PAGADA,
        expediente="EXP-EDIT-PAGADA-001",
    )
    comprobante = crear_comprobante(liquidacion, activo=True)
    return liquidacion, comprobante


@pytest.fixture
def otra_liquidacion_con_comprobante(
    crear_liquidacion,
    crear_comprobante,
    segundo_proyecto,
):
    """A second liquidacion (different proyecto) with its own ACTIVE comprobante."""
    liquidacion = crear_liquidacion(
        proyecto_override=segundo_proyecto,
        expediente="EXP-EDIT-OTRA-001",
    )
    comprobante = crear_comprobante(liquidacion, activo=True)
    return liquidacion, comprobante


# ── 404 — liquidacion inexistente ──────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_404_for_nonexistent_liquidacion(auth_client):
    """
    GIVEN: a liquidacion id that does not exist
    WHEN: the client sends the PATCH
    THEN: 404 and no comprobante is created or modified.
    """
    comprobantes_before = LiquidacionComprobante.objects.count()

    response = auth_client.patch(
        _url(uuid.uuid4(), uuid.uuid4()),
        json=_payload(),
    )

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert LiquidacionComprobante.objects.count() == comprobantes_before


# ── 404 — comprobante inexistente ──────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_404_for_nonexistent_comprobante(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: an existing liquidacion
    WHEN: the client sends the PATCH with a non-existent comprobante id
    THEN: 404 and the active comprobante stays untouched.
    """
    liquidacion, comprobante = liquidacion_con_comprobante

    response = auth_client.patch(
        _url(liquidacion.id, uuid.uuid4()),
        json=_payload(),
    )

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"
    assert response.json()["error"]["code"] == "NOT_FOUND"

    comprobante.refresh_from_db()
    assert comprobante.serie == "F001"
    assert comprobante.numero == "0001-2026"


# ── 404 — comprobante de otra liquidacion ─────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_404_for_comprobante_of_another_liquidacion(
    auth_client,
    liquidacion_con_comprobante,
    otra_liquidacion_con_comprobante,
):
    """
    GIVEN: two liquidaciones, each with its own active comprobante
    WHEN: the client mixes the liquidacion id and the comprobante id
    THEN: 404 — the comprobante is scoped to its liquidacion.
    """
    liquidacion, _comprobante = liquidacion_con_comprobante
    _otra_liquidacion, comprobante_ajeno = otra_liquidacion_con_comprobante

    response = auth_client.patch(
        _url(liquidacion.id, comprobante_ajeno.id),
        json=_payload(),
    )

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"

    comprobante_ajeno.refresh_from_db()
    assert comprobante_ajeno.serie == "F001"
    assert comprobante_ajeno.activo is True


# ── 404 — liquidacion sin comprobantes ─────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_404_when_liquidacion_has_no_comprobantes(
    auth_client,
    liquidacion_sin_comprobantes,
):
    """
    GIVEN: a liquidacion without any comprobante
    WHEN: the client sends the PATCH
    THEN: 404 and no comprobante is created.
    """
    response = auth_client.patch(
        _url(liquidacion_sin_comprobantes.id, uuid.uuid4()),
        json=_payload(),
    )

    assert response.status_code == 404, \
        f"Expected 404, got {response.status_code}: {response.content}"
    assert liquidacion_sin_comprobantes.comprobantes.count() == 0


# ── 409 — comprobante historico ────────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_409_for_historical_comprobante(
    auth_client,
    liquidacion_con_historico,
):
    """
    GIVEN: a liquidacion with an active comprobante and a historical one
    WHEN: the client tries to edit the historical comprobante
    THEN: 409 with the COMPROBANTE_NO_ACTIVO code; both rows stay unchanged.
    """
    liquidacion, activo, historico = liquidacion_con_historico

    response = auth_client.patch(
        _url(liquidacion.id, historico.id),
        json=_payload(serie="HACK", numero="HACK"),
    )

    assert response.status_code == 409, \
        f"Expected 409, got {response.status_code}: {response.content}"
    assert response.json()["error"]["code"] == "COMPROBANTE_NO_ACTIVO"

    historico.refresh_from_db()
    assert historico.serie == "B001"
    assert historico.numero == "0001-2025"
    assert historico.activo is False

    activo.refresh_from_db()
    assert activo.activo is True
    assert activo.serie == "F001"


# ── Update in-place real ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_updates_the_active_row_in_place(
    auth_client,
    liquidacion_con_historico,
):
    """
    GIVEN: a liquidacion with an active comprobante and a historical one
    WHEN: the client edits the active comprobante
    THEN: 200 with the new values, the same comprobante id, the same number of
          comprobantes and exactly one active comprobante.
    """
    liquidacion, activo, _historico = liquidacion_con_historico
    comprobantes_before = liquidacion.comprobantes.count()
    comprobante_id = activo.id

    response = auth_client.patch(
        _url(liquidacion.id, activo.id),
        json=_payload(serie="F002", numero="0002-2026", fecha_emision="2026-11-15"),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    activo.refresh_from_db()
    assert activo.id == comprobante_id
    assert activo.serie == "F002"
    assert activo.numero == "0002-2026"
    assert activo.fecha_emision == date(2026, 11, 15)

    assert liquidacion.comprobantes.count() == comprobantes_before
    assert liquidacion.comprobantes.filter(activo=True).count() == 1


@pytest.mark.django_db
def test_editar_comprobante_does_not_create_a_second_row(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: a liquidacion with one active comprobante
    WHEN: the client edits that comprobante
    THEN: the comprobante count and the comprobante id are the same.
    """
    liquidacion, comprobante = liquidacion_con_comprobante
    comprobantes_before = liquidacion.comprobantes.count()

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    assert liquidacion.comprobantes.count() == comprobantes_before

    comprobantes = list(liquidacion.comprobantes.all())
    assert len(comprobantes) == 1
    assert comprobantes[0].id == comprobante.id


# ── monto preservado ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_preserves_monto(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: an active comprobante with monto = 1500.00
    WHEN: the client edits its serie and numero
    THEN: the persisted monto is still 1500.00.
    """
    liquidacion, comprobante = liquidacion_con_comprobante
    monto_before = comprobante.monto

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(serie="F009", numero="0009-2026"),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    comprobante.refresh_from_db()
    assert comprobante.monto == monto_before
    assert comprobante.monto == Decimal("1500.00")


@pytest.mark.django_db
def test_editar_comprobante_ignores_monto_sent_by_the_client(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: an active comprobante with monto = 1500.00
    WHEN: the client sends a `monto` in the body
    THEN: the persisted monto is NOT overwritten.
    """
    liquidacion, comprobante = liquidacion_con_comprobante

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(monto=9999.99),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    comprobante.refresh_from_db()
    assert comprobante.monto == Decimal("1500.00")


def test_monto_is_not_an_input_field_of_the_update_schema():
    """
    GIVEN: the input schema of the PATCH
    WHEN: its contract is inspected
    THEN: it does not declare a `monto` field.
    """
    assert "monto" not in LiquidacionComprobanteUpdateIn.model_fields


@pytest.mark.django_db
def test_editar_comprobante_does_not_touch_motivo_reemplazo(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: an active comprobante with motivo_reemplazo = "Comprobante anterior anulado"
    WHEN: the client sends the PATCH
    THEN: the motivo_reemplazo is unchanged.
    """
    liquidacion, comprobante = liquidacion_con_comprobante
    comprobante.motivo_reemplazo = "Comprobante anterior anulado"
    comprobante.save(update_fields=["motivo_reemplazo"])

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    comprobante.refresh_from_db()
    assert comprobante.motivo_reemplazo == "Comprobante anterior anulado"


# ── Paridad de estado con el POST (sin guard PAGADA) ──────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_does_not_block_pagada_liquidacion(
    auth_client,
    liquidacion_pagada_con_comprobante,
):
    """
    GIVEN: a PAGADA liquidacion with an active comprobante
    WHEN: the client edits the active comprobante
    THEN: 200 — no PAGADA guard (parity with POST /comprobante).
    """
    liquidacion, comprobante = liquidacion_pagada_con_comprobante

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(serie="F500"),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    comprobante.refresh_from_db()
    assert comprobante.serie == "F500"


# ── La edicion no crea revisiones ──────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_does_not_change_numero_revision(
    auth_client,
    crear_liquidacion,
    crear_comprobante,
):
    """
    GIVEN: a liquidacion with numero_revision = 2
    WHEN: the client edits its active comprobante
    THEN: the numero_revision is still 2.
    """
    liquidacion = crear_liquidacion(
        expediente="EXP-EDIT-REVISION-002",
        numero_revision=2,
    )
    comprobante = crear_comprobante(liquidacion, activo=True)

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    liquidacion.refresh_from_db()
    assert liquidacion.numero_revision == 2


# ── Envelope ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_editar_comprobante_returns_standard_api_response_envelope(
    auth_client,
    liquidacion_con_comprobante,
):
    """
    GIVEN: an active comprobante
    WHEN: the client sends the PATCH
    THEN: the response is the standard envelope (success/message/data) and the
          data payload exposes the comprobantes of the liquidacion.
    """
    liquidacion, comprobante = liquidacion_con_comprobante

    response = auth_client.patch(
        _url(liquidacion.id, comprobante.id),
        json=_payload(),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Comprobante actualizado correctamente."

    data = body["data"]
    assert data["id"] == str(liquidacion.id)

    comprobantes = data["comprobantes"]
    assert len(comprobantes) == 1
    assert comprobantes[0]["id"] == str(comprobante.id)
    assert comprobantes[0]["activo"] is True
    assert comprobantes[0]["monto"] == 1500.0
