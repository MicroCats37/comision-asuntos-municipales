"""
Integration tests for the REPEATABLE historical number of the typed legacy
routes (Phase 3, task 3.1 — "explicit repeated numero allowed").

Decision D2 of the change: `numero` is an INFORMATIVE historical datum. It is
persisted verbatim, it MAY repeat, there is no uniqueness rule, no constraint,
no duplicate validation and NO 409 conflict.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_legacy_m2,
    make_payload_legacy_po,
)


NUMERO_REPETIDO = 5150


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_registro_legacy_acepta_el_mismo_numero_dos_veces(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy de Edificaciones ya creado con un número.
    WHEN:  se crea OTRO registro legacy del mismo tipo con el MISMO número.
    THEN:  la creación tiene éxito (no hay 409 ni error de integridad) y AMBOS
           registros conservan el número repetido.
    """
    fecha_registro = catalogo_legacy_historico["fecha_registro"]

    primera = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=NUMERO_REPETIDO,
        fecha_registro=fecha_registro,
        expediente="EXP-REPETIDO-001",
    )
    segunda = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=NUMERO_REPETIDO,
        fecha_registro=fecha_registro,
        expediente="EXP-REPETIDO-002",
    )

    response_1 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=primera,
    )
    assert response_1.status_code == 200, (
        f"Expected 200 on the first creation, got {response_1.status_code}: {response_1.content}"
    )

    response_2 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=segunda,
    )
    assert response_2.status_code == 200, (
        f"Expected 200 on the repeated numero, got {response_2.status_code}: {response_2.content}"
    )

    # Ambos wrappers conservan el número repetido.
    numero_1 = response_1.json()["data"]["liquidacion_especifica"]["numero"]
    numero_2 = response_2.json()["data"]["liquidacion_especifica"]["numero"]
    assert numero_1 == NUMERO_REPETIDO
    assert numero_2 == NUMERO_REPETIDO

    # Y la base guarda las dos filas con el mismo número (no hay unicidad).
    assert LiquidacionEdificacion.objects.filter(numero=NUMERO_REPETIDO).count() == 2


@pytest.mark.django_db
def test_registro_legacy_m2_acepta_el_mismo_numero_dos_veces(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy de Habilitación Urbana ya creado con un número.
    WHEN:  se crea OTRO registro legacy del mismo tipo con el MISMO número.
    THEN:  la creación tiene éxito y ambos wrappers conservan el número.
    """
    fecha_registro = catalogo_legacy_historico["fecha_registro"]
    tarifa_id = catalogo_legacy_historico["tarifa_m2_habilitacion_urbana"].id

    for expediente in ("EXP-REPETIDO-M2-001", "EXP-REPETIDO-M2-002"):
        payload = make_payload_legacy_m2(
            municipalidad.id,
            municipalidad.distrito_id,
            tarifa_id,
            numero=NUMERO_REPETIDO,
            fecha_registro=fecha_registro,
            expediente=expediente,
        )
        response = auth_client.post(
            "/liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy",
            json=payload,
        )
        assert response.status_code == 200, (
            f"Expected 200 for {expediente}, got {response.status_code}: {response.content}"
        )
        assert response.json()["data"]["liquidacion_especifica"]["numero"] == NUMERO_REPETIDO

    assert LiquidacionHabilitacionUrbana.objects.filter(numero=NUMERO_REPETIDO).count() == 2


@pytest.mark.django_db
def test_registro_legacy_no_rechaza_con_409_un_numero_repetido(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un número ya usado por otro registro legacy del mismo tipo.
    WHEN:  se reintenta la creación con ese número.
    THEN:  la respuesta NO es 409 (el número no es una barrera de unicidad).
    """
    fecha_registro = catalogo_legacy_historico["fecha_registro"]

    def _payload(expediente):
        return make_payload_legacy_po(
            municipalidad.id,
            municipalidad.distrito_id,
            numero=NUMERO_REPETIDO,
            fecha_registro=fecha_registro,
            expediente=expediente,
        )

    auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=_payload("EXP-REPETIDO-003"),
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=_payload("EXP-REPETIDO-004"),
    )

    assert response.status_code != 409, (
        f"A repeated legacy numero must not produce 409, got {response.status_code}: {response.content}"
    )
    assert response.status_code == 200
