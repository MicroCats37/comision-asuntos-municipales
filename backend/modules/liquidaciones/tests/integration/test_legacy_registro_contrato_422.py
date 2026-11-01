"""
Integration tests for the 422 contract of the typed legacy routes
(Phase 3, task 3.1 — "client attempts to control server fields").

The composed legacy input declares `extra="forbid"` at EVERY level, so the
client cannot control the fields that belong to the server:

- `legacy` — the flag is assigned by the SERVER (the route is the
  discriminator). Sending it is rejected.
- `cotizacion_legacy` — the legacy totals bypass (manual sub_total/total).
  Rejected: the totals are ALWAYS computed.
- `uit_valor_override` / `uit_id_override` — the financial bypasses.
  Rejected: IGV/UIT/tarifas/derechos are ALWAYS resolved by date.
- any other unknown field — rejected.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_legacy_io,
    make_payload_legacy_m2,
    make_payload_legacy_po,
)


# ── Rutas legacy tipadas ────────────────────────────────────────────────────

RUTA_LEGACY = {
    "edificaciones": "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
    "taludes": "/liquidaciones/taludes/nueva-liquidacion/legacy",
    "impacto-vial": "/liquidaciones/impacto-vial/nueva-liquidacion/legacy",
    "habilitacion-urbana": "/liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy",
    "mecanica-suelos": "/liquidaciones/mecanica-suelos/nueva-liquidacion/legacy",
    "inspeccion-obra": "/liquidaciones/inspeccion-obra/nueva-liquidacion/legacy",
}

# (slug, motor, clave de la tarifa en el catálogo histórico)
MOTORES = [
    ("edificaciones", "po", "tarifa_po_edificacion"),
    ("habilitacion-urbana", "m2", "tarifa_m2_habilitacion_urbana"),
    ("inspeccion-obra", "visitas", "tarifa_visitas_inspeccion_obra"),
]

# Campos que el cliente NO puede enviar (todos a nivel raíz del payload).
CAMPOS_PROHIBIDOS = [
    ("legacy", True),
    ("cotizacion_legacy", {"sub_total": "1000.00", "total": "1180.00"}),
    ("uit_valor_override", 4950),
    ("uit_id_override", "00000000-0000-0000-0000-000000000000"),
    ("subtotal_manual", 1000.00),
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _payload_valido(motor, catalogo, municipalidad, numero, fecha_registro):
    """Construye un payload legacy VÁLIDO para el motor pedido."""
    if motor == "po":
        return make_payload_legacy_po(
            municipalidad.id,
            municipalidad.distrito_id,
            numero=numero,
            fecha_registro=fecha_registro,
        )
    if motor == "m2":
        return make_payload_legacy_m2(
            municipalidad.id,
            municipalidad.distrito_id,
            catalogo["tarifa_key"],
            numero=numero,
            fecha_registro=fecha_registro,
        )
    return make_payload_legacy_io(
        municipalidad.id,
        municipalidad.distrito_id,
        catalogo["tarifa_key"],
        numero=numero,
        fecha_registro=fecha_registro,
    )


def _catalogo_con_tarifa(catalogo_legacy_historico, tarifa_key):
    """Devuelve el catálogo con la tarifa del motor ya resuelta en `tarifa_key`."""
    catalogo = dict(catalogo_legacy_historico)
    catalogo["tarifa_key"] = catalogo[tarifa_key]
    return catalogo


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("tipo_slug", sorted(RUTA_LEGACY))
def test_registro_legacy_rechaza_el_flag_legacy_del_cliente(
    tipo_slug,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un payload legacy que además envía `legacy=true`.
    WHEN:  se manda a la ruta legacy del tipo.
    THEN:  422 — el flag es del servidor (la ruta es el discriminador).
    """
    motor = {
        "edificaciones": "po",
        "taludes": "po",
        "impacto-vial": "po",
        "habilitacion-urbana": "m2",
        "mecanica-suelos": "m2",
        "inspeccion-obra": "visitas",
    }[tipo_slug]
    tarifa_key = {
        "edificaciones": "tarifa_po_edificacion",
        "taludes": "tarifa_po_taludes",
        "impacto-vial": "tarifa_po_impacto_vial",
        "habilitacion-urbana": "tarifa_m2_habilitacion_urbana",
        "mecanica-suelos": "tarifa_m2_mecanica_suelos",
        "inspeccion-obra": "tarifa_visitas_inspeccion_obra",
    }[tipo_slug]

    catalogo = _catalogo_con_tarifa(catalogo_legacy_historico, tarifa_key)
    payload = _payload_valido(
        motor,
        catalogo,
        municipalidad,
        9101,
        catalogo["fecha_registro"],
    )
    payload["legacy"] = True

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for a client-sent `legacy` flag on {tipo_slug}, "
        f"got {response.status_code}: {response.content}"
    )
    assert LiquidacionGeneral.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,motor,tarifa_key",
    MOTORES,
    ids=[m[0] for m in MOTORES],
)
@pytest.mark.parametrize("campo,valor", CAMPOS_PROHIBIDOS, ids=[c[0] for c in CAMPOS_PROHIBIDOS])
def test_registro_legacy_rechaza_los_campos_controlados_por_el_servidor(
    tipo_slug,
    motor,
    tarifa_key,
    campo,
    valor,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un payload legacy válido que además envía un campo prohibido
           (totales manuales, overrides financieros o cualquier otro extra).
    WHEN:  se manda a la ruta legacy del tipo.
    THEN:  422 y NINGUNA fila queda persistida.

    El rechazo es un contrato de SCHEMA (`extra="forbid"`), no de negocio: se
    comprueba en un motor por familia (PO / M2 / Visitas) para no duplicar la
    misma aserción seis veces.
    """
    catalogo = _catalogo_con_tarifa(catalogo_legacy_historico, tarifa_key)
    payload = _payload_valido(
        motor,
        catalogo,
        municipalidad,
        9102,
        catalogo["fecha_registro"],
    )
    payload[campo] = valor

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for the forbidden field `{campo}` on {tipo_slug}, "
        f"got {response.status_code}: {response.content}"
    )
    assert LiquidacionGeneral.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,motor,tarifa_key",
    MOTORES,
    ids=[m[0] for m in MOTORES],
)
def test_registro_legacy_rechaza_los_totales_manuales_anidados(
    tipo_slug,
    motor,
    tarifa_key,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un payload legacy que esconde el bypass de totales dentro del
           bloque específico (`liquidacion_especifica.cotizacion_legacy`).
    WHEN:  se manda a la ruta legacy del tipo.
    THEN:  422 — el bloque específico también es estricto.
    """
    catalogo = _catalogo_con_tarifa(catalogo_legacy_historico, tarifa_key)
    payload = _payload_valido(
        motor,
        catalogo,
        municipalidad,
        9103,
        catalogo["fecha_registro"],
    )
    payload["liquidacion_especifica"]["cotizacion_legacy"] = {
        "sub_total": "1000.00",
        "total": "1180.00",
    }

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for a nested `cotizacion_legacy` on {tipo_slug}, "
        f"got {response.status_code}: {response.content}"
    )
    assert LiquidacionGeneral.objects.count() == 0


@pytest.mark.django_db
def test_registro_legacy_rechaza_los_totales_manuales_anidados_en_datos_po(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un payload legacy PO que esconde el bypass dentro de `datos`.
    WHEN:  se manda a la ruta legacy de Edificaciones.
    THEN:  422 — el bloque `datos` también es estricto.
    """
    catalogo = _catalogo_con_tarifa(catalogo_legacy_historico, "tarifa_po_edificacion")
    payload = _payload_valido(
        "po",
        catalogo,
        municipalidad,
        9104,
        catalogo["fecha_registro"],
    )
    payload["liquidacion_especifica"]["datos"]["sub_total"] = 1000.00

    response = auth_client.post(RUTA_LEGACY["edificaciones"], json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for a nested manual total, got {response.status_code}: {response.content}"
    )
    assert LiquidacionGeneral.objects.count() == 0
