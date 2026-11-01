"""
Integration tests for the HISTORICAL TOTALS of the typed legacy routes
(Phase 3, task 3.1 — "historical totals").

Decision D3 of the change: the totals of a manual legacy registration are
ALWAYS computed with the tariffs, IGV, UIT and rights effective on
`fecha_registro`. There is no manual total and no bypass.

The historical catalog (`tests/fixtures/legacy_historico_fixtures.py`) lives in
2023 with values deliberately DIFFERENT from the current ones:

    UIT            4950 (2023)  vs 5150 (current)
    Tarifa PO      0.20 % (2023) vs 0.10 % (current)
    Costo M2 HU    100.00 (2023) vs 150.00 (current)
    Costo M2 MS    120.00 (2023) vs 150.00 (current)

So an implementation that resolved today's values would produce a different
number in EVERY assertion below.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_legacy_io,
    make_payload_legacy_m2,
    make_payload_legacy_po,
)


IGV = Decimal("0.18")
UIT_HISTORICA = Decimal("4950")

# ── Expectations per engine (PO: 3 especialidades × 0.20 %; Taludes/IV: 1 × 0.20 %) ──
ESPECIALIDADES_EDIFICACIONES = 3

VALOR_DECLARADO_PO = Decimal("1000000.00")
PORCENTAJE_EDIFICACIONES = Decimal("0.0060")  # 3 × 0.0020
SUBTOTAL_EDIFICACIONES = Decimal("6000.00")
TOTAL_EDIFICACIONES = Decimal("7080.00")  # 6000 × 1.18

PORCENTAJE_UNA_ESPECIALIDAD = Decimal("0.0020")  # 1 × 0.0020
SUBTOTAL_UNA_ESPECIALIDAD = Decimal("2000.00")
TOTAL_UNA_ESPECIALIDAD = Decimal("2360.00")  # 2000 × 1.18

AREA_M2 = Decimal("100")
COSTO_M2_HU_HISTORICO = Decimal("100.0000")
TOTAL_M2_HU = Decimal("10000.00")  # 100 m² × 100.00 (bruto, IGV incluido)
SUBTOTAL_M2_HU = Decimal("8474.58")  # 10000 / 1.18

COSTO_M2_MS_HISTORICO = Decimal("120.0000")
TOTAL_M2_MS = Decimal("12000.00")  # 100 m² × 120.00 (bruto, IGV incluido)
SUBTOTAL_M2_MS = Decimal("10169.49")  # 12000 / 1.18

CANTIDAD_VISITAS = 3
PORCENTAJE_UIT_VISITAS = Decimal("0.05")
SUBTOTAL_VISITAS = Decimal("742.50")  # 3 × (0.05 × 4950)
TOTAL_VISITAS = Decimal("876.15")  # 742.50 × 1.18


def _dec(valor) -> Decimal:
    """Normaliza un decimal de la API a `Decimal` (la API puede serializar texto o float)."""
    return Decimal(str(valor))


def _crear_legacy_edificaciones(auth_client, municipalidad, catalogo, numero, valor_declarado, expediente):
    """Crea un registro legacy de Edificaciones y devuelve los wrappers."""
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=numero,
        fecha_registro=catalogo["fecha_registro"],
        valor_declarado=valor_declarado,
        expediente=expediente,
    )
    response = auth_client.post("/liquidaciones/edificaciones/nueva-liquidacion/legacy", json=payload)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    return response.json()["data"]


# ── Motor PorcentajeObra ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_registro_legacy_edificaciones_calcula_con_tarifas_historicas(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 (3 especialidades habilitadas, tarifa 0.20 %).
    WHEN:  se registra una Edificación legacy con fecha 2023-06-15.
    THEN:  los totales se calculan con la tarifa histórica (0.60 % acumulado),
           no con la vigente, y se aplican la UIT y el IGV de esa fecha.
    """
    result = _crear_legacy_edificaciones(
        auth_client,
        municipalidad,
        catalogo_legacy_historico,
        7301,
        VALOR_DECLARADO_PO,
        "EXP-HIST-EDIF-001",
    )

    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    assert _dec(lt["porcentaje_liquidacion"]) == PORCENTAJE_EDIFICACIONES
    assert len(lt["detalles"]) == ESPECIALIDADES_EDIFICACIONES
    assert _dec(lg["sub_total"]) == SUBTOTAL_EDIFICACIONES
    assert _dec(lg["total"]) == TOTAL_EDIFICACIONES

    # La UIT aplicada es la de la FECHA DEL REGISTRO (4950), no la vigente (5150).
    assert _dec(lg["uit"]["valor"]) == UIT_HISTORICA
    assert _dec(lg["igv"]["valor"]) == IGV


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,numero",
    [
        ("taludes", 7302),
        ("impacto-vial", 7303),
    ],
)
def test_registro_legacy_po_de_una_especialidad_calcula_con_tarifa_historica(
    tipo_slug,
    numero,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 de Taludes / Impacto Vial (1 especialidad,
           tarifa 0.20 %).
    WHEN:  se registra una liquidación legacy con fecha 2023-06-15.
    THEN:  los totales se calculan con la tarifa histórica (0.20 %) y la UIT de esa fecha.
    """
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=numero,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        valor_declarado=VALOR_DECLARADO_PO,
        expediente=f"EXP-HIST-{tipo_slug.upper()}-001",
    )
    response = auth_client.post(
        f"/liquidaciones/{tipo_slug}/nueva-liquidacion/legacy",
        json=payload,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    assert _dec(lt["porcentaje_liquidacion"]) == PORCENTAJE_UNA_ESPECIALIDAD
    assert len(lt["detalles"]) == 1
    assert _dec(lg["sub_total"]) == SUBTOTAL_UNA_ESPECIALIDAD
    assert _dec(lg["total"]) == TOTAL_UNA_ESPECIALIDAD
    assert _dec(lg["uit"]["valor"]) == UIT_HISTORICA


# ── Motor Por Metro Cuadrado ────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize(
    "tipo_slug,tarifa_key,costo_por_m2,subtotal_esperado,total_esperado",
    [
        (
            "habilitacion-urbana",
            "tarifa_m2_habilitacion_urbana",
            COSTO_M2_HU_HISTORICO,
            SUBTOTAL_M2_HU,
            TOTAL_M2_HU,
        ),
        (
            "mecanica-suelos",
            "tarifa_m2_mecanica_suelos",
            COSTO_M2_MS_HISTORICO,
            SUBTOTAL_M2_MS,
            TOTAL_M2_MS,
        ),
    ],
    ids=["habilitacion-urbana", "mecanica-suelos"],
)
def test_registro_legacy_m2_calcula_con_tarifa_historica(
    tipo_slug,
    tarifa_key,
    costo_por_m2,
    subtotal_esperado,
    total_esperado,
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 (costo por m² propio de cada tipo).
    WHEN:  se registra una liquidación legacy M2 con fecha 2023-06-15.
    THEN:  el costo por m² aplicado es el de esa fecha (no el vigente) y los
           totales se derivan de él con el IGV histórico.
    """
    payload = make_payload_legacy_m2(
        municipalidad.id,
        municipalidad.distrito_id,
        catalogo_legacy_historico[tarifa_key].id,
        numero=7304,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        area_solicitada=float(AREA_M2),
        expediente="EXP-HIST-M2-001",
    )
    response = auth_client.post(
        f"/liquidaciones/{tipo_slug}/nueva-liquidacion/legacy",
        json=payload,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    assert _dec(lt["costo_por_m2"]) == costo_por_m2
    assert _dec(lg["sub_total"]) == subtotal_esperado
    assert _dec(lg["total"]) == total_esperado
    assert _dec(lg["uit"]["valor"]) == UIT_HISTORICA


# ── Motor Visitas (Inspección de Obra) ──────────────────────────────────────

@pytest.mark.django_db
def test_registro_legacy_inspeccion_obra_calcula_con_tarifa_historica(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 (5 % de la UIT por visita).
    WHEN:  se registra una Inspección de Obra legacy con fecha 2023-06-15.
    THEN:  el subtotal es visitas × (5 % × UIT de esa fecha) y el total aplica el
           IGV de esa fecha.
    """
    payload = make_payload_legacy_io(
        municipalidad.id,
        municipalidad.distrito_id,
        catalogo_legacy_historico["tarifa_visitas_inspeccion_obra"].id,
        numero=7305,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        cantidad_visitas=CANTIDAD_VISITAS,
        expediente="EXP-HIST-IO-001",
    )
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion/legacy",
        json=payload,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    assert _dec(lt["porcentaje_uit"]) == PORCENTAJE_UIT_VISITAS
    assert _dec(lg["sub_total"]) == SUBTOTAL_VISITAS
    assert _dec(lg["total"]) == TOTAL_VISITAS
    assert _dec(lg["uit"]["valor"]) == UIT_HISTORICA


# ── No hay bypass: los totales manuales no alteran el resultado ─────────────

@pytest.mark.django_db
def test_registro_legacy_ignora_cualquier_intento_de_total_manual_en_el_bloque_general(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un payload legacy con un campo `sub_total` en el bloque general
           (el bloque general es estricto).
    WHEN:  se manda a la ruta legacy.
    THEN:  422 — no existe ninguna vía para fijar los importes a mano.
    """
    payload = make_payload_legacy_po(
        municipalidad.id,
        municipalidad.distrito_id,
        numero=7306,
        fecha_registro=catalogo_legacy_historico["fecha_registro"],
        valor_declarado=VALOR_DECLARADO_PO,
        expediente="EXP-HIST-EDIF-002",
    )
    payload["liquidacion_general"]["sub_total"] = 1.00

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=payload,
    )

    assert response.status_code == 422, (
        f"Expected 422 for a manual subtotal in the general block, "
        f"got {response.status_code}: {response.content}"
    )
