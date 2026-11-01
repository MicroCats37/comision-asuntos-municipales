"""
Integration tests for the TYPED legacy registration routes (Phase 3, task 3.1).

`POST /liquidaciones/{tipo}/nueva-liquidacion/legacy` for the six types:
Edificaciones, Taludes, Impacto Vial, Habilitación Urbana, Mecánica de
Suelos and Inspección de Obra.

What this file proves (per type, parametrized):
- the route creates the record through the CURRENT atomic create flow and
  returns the EXISTING typed wrappers (`liquidacion_general`,
  `liquidacion_especifica`, `liquidacion_tipo`);
- `legacy=true` is assigned SERVER-SIDE (the flag is the route discriminator,
  the client never sends it);
- the explicit `numero` is persisted verbatim in the type-specific wrapper;
- the explicit `fecha_registro` is persisted as the effective date of the
  record;
- the record starts in the existing `PENDIENTE` state (no special legacy
  state is introduced).

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest
from decimal import Decimal

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

# (slug, motor, clave de la tarifa en el catálogo histórico, numero, valor declarado)
TIPOS_LEGACY = [
    ("edificaciones", "po", "tarifa_po_edificacion", 4242, 1000000.00),
    ("taludes", "po", "tarifa_po_taludes", 4243, 1000000.00),
    ("impacto-vial", "po", "tarifa_po_impacto_vial", 4244, 1000000.00),
    ("habilitacion-urbana", "m2", "tarifa_m2_habilitacion_urbana", 4245, None),
    ("mecanica-suelos", "m2", "tarifa_m2_mecanica_suelos", 4246, None),
    ("inspeccion-obra", "visitas", "tarifa_visitas_inspeccion_obra", 4247, None),
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _dec(valor) -> Decimal:
    """Normaliza un decimal de la API a `Decimal` (la API puede serializar texto o float)."""
    return Decimal(str(valor))


def _payload_legacy(motor, catalogo, municipalidad, distrito_id, numero, fecha_registro, valor_declarado):
    """Construye el payload legacy del motor pedido usando el catálogo histórico."""
    if motor == "po":
        return make_payload_legacy_po(
            municipalidad.id,
            distrito_id,
            numero=numero,
            fecha_registro=fecha_registro,
            valor_declarado=valor_declarado,
            expediente=f"EXP-LEGACY-{numero}",
        )
    if motor == "m2":
        return make_payload_legacy_m2(
            municipalidad.id,
            distrito_id,
            catalogo["tarifa_key"],
            numero=numero,
            fecha_registro=fecha_registro,
            expediente=f"EXP-LEGACY-{numero}",
        )
    return make_payload_legacy_io(
        municipalidad.id,
        distrito_id,
        catalogo["tarifa_key"],
        numero=numero,
        fecha_registro=fecha_registro,
        expediente=f"EXP-LEGACY-{numero}",
    )


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,motor,tarifa_key,numero,valor_declarado",
    TIPOS_LEGACY,
    ids=[t[0] for t in TIPOS_LEGACY],
)
def test_registro_legacy_crea_con_flag_numero_y_fecha(
    tipo_slug,
    motor,
    tarifa_key,
    numero,
    valor_declarado,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un operador autenticado envía los datos del formulario vigente más
           `numero` y `fecha_registro` por la ruta legacy del tipo.
    WHEN:  se llama a la ruta legacy.
    THEN:  200 con los tres wrappers tipados de siempre, `legacy=true` asignado
           por el servidor, `numero` persistido tal cual, `fecha_registro`
           persistida y estado `PENDIENTE`.
    """
    catalogo = dict(catalogo_legacy_historico)
    catalogo["tarifa_key"] = catalogo[tarifa_key]
    fecha_registro = catalogo["fecha_registro"]

    payload = _payload_legacy(
        motor,
        catalogo,
        municipalidad,
        municipalidad.distrito_id,
        numero,
        fecha_registro,
        valor_declarado,
    )

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)

    assert response.status_code == 200, (
        f"Expected 200 for {tipo_slug}, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True

    result = data["data"]
    assert "liquidacion_general" in result
    assert "liquidacion_especifica" in result
    assert "liquidacion_tipo" in result

    lg = result["liquidacion_general"]
    le = result["liquidacion_especifica"]

    # El flag `legacy` lo asigna el SERVIDOR (la ruta es el discriminador).
    assert lg["legacy"] is True, "The server must set legacy=true on the typed legacy route"

    # Estado inicial: el existente PENDIENTE (no hay estado especial legacy).
    assert lg["estado"] == "PENDIENTE"

    # El número explícito se persiste tal cual en el wrapper específico.
    assert le["numero"] == numero, f"Expected numero={numero}, got {le['numero']}"

    # La fecha de registro explícita se persiste como fecha efectiva.
    assert lg["fecha_registro"].startswith(fecha_registro.isoformat()), (
        f"Expected fecha_registro={fecha_registro.isoformat()}, got {lg['fecha_registro']}"
    )

    # IO es revision-less: siempre revisión 1. Los demás tipos reciben la del payload.
    assert lg["numero_revision"] == 1

    assert lg["expediente"] == f"EXP-LEGACY-{numero}"
    assert str(lg["usuario_creador"]["id"]) == str(auth_client.user.id)

    # Los totales SIEMPRE se calculan: nunca hay totales manuales.
    assert _dec(lg["sub_total"]) > 0
    assert _dec(lg["total"]) >= _dec(lg["sub_total"])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,motor,tarifa_key,numero,valor_declarado",
    TIPOS_LEGACY,
    ids=[t[0] for t in TIPOS_LEGACY],
)
def test_registro_legacy_persiste_el_flag_y_la_fecha_en_la_base(
    tipo_slug,
    motor,
    tarifa_key,
    numero,
    valor_declarado,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un registro legacy creado por la ruta tipada.
    WHEN:  se lee la fila persistida.
    THEN:  `legacy=True` y `fecha_registro` quedaron persistidos en la base.
    """
    catalogo = dict(catalogo_legacy_historico)
    catalogo["tarifa_key"] = catalogo[tarifa_key]
    fecha_registro = catalogo["fecha_registro"]

    payload = _payload_legacy(
        motor,
        catalogo,
        municipalidad,
        municipalidad.distrito_id,
        numero,
        fecha_registro,
        valor_declarado,
    )

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)
    assert response.status_code == 200, (
        f"Expected 200 for {tipo_slug}, got {response.status_code}: {response.content}"
    )

    liquidacion_id = response.json()["data"]["liquidacion_general"]["id"]

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.legacy is True
    assert lg.fecha_registro.date() == fecha_registro
    assert lg.estado == "PENDIENTE"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,motor,tarifa_key,numero,valor_declarado",
    TIPOS_LEGACY,
    ids=[t[0] for t in TIPOS_LEGACY],
)
def test_registro_legacy_devuelve_los_mismos_wrappers_que_el_registro_normal(
    tipo_slug,
    motor,
    tarifa_key,
    numero,
    valor_declarado,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: la ruta legacy.
    WHEN:  se responde.
    THEN:  la respuesta tiene EXACTAMENTE la misma forma de wrappers que la
           ruta normal de creación (contrato de wrappers tipados).
    """
    catalogo = dict(catalogo_legacy_historico)
    catalogo["tarifa_key"] = catalogo[tarifa_key]
    fecha_registro = catalogo["fecha_registro"]

    payload = _payload_legacy(
        motor,
        catalogo,
        municipalidad,
        municipalidad.distrito_id,
        numero,
        fecha_registro,
        valor_declarado,
    )

    response = auth_client.post(RUTA_LEGACY[tipo_slug], json=payload)
    assert response.status_code == 200, (
        f"Expected 200 for {tipo_slug}, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    assert set(result.keys()) == {"liquidacion_general", "liquidacion_especifica", "liquidacion_tipo"}

    # El wrapper de identidad sólo expone id + numero.
    assert set(result["liquidacion_especifica"].keys()) == {"id", "numero"}

    # El wrapper general expone el flag legacy (contrato del badge Legacy).
    assert "legacy" in result["liquidacion_general"]
    assert "fecha_registro" in result["liquidacion_general"]
    assert "estado" in result["liquidacion_general"]
