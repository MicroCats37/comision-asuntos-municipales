"""
Integration tests for the OPTIONAL EFFECTIVE DATE on quote and tariff lookup
(Phase 3, task 3.2 — "optional-effective-date quote/tariff regression").

Requirement (Historical quote preview): the current quote and tariff lookup
flows MUST accept an optional effective date. WITHOUT a date they MUST
preserve the current behavior.

What this file proves:
- `/tarifas/vigentes?fecha=...` resolves the catalog of THAT date;
- `/tarifas/vigentes` (no date) still resolves today's catalog — unchanged;
- `/cotizar?fecha=...` computes with the values of THAT date, even when the
  payload carries a tariff of another date (the date governs);
- `/cotizar` (no date) still computes with today's values — unchanged.

The historical catalog (2023) and the current one (2024+) differ in every
value, so a wrong resolution is visible in the assertions.

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.tests.fixtures.factories import make_payload_m2_cotizar


COSTO_M2_HISTORICO = Decimal("100.0000")
COSTO_M2_VIGENTE = Decimal("150.0000")
TOTAL_M2_HISTORICO = Decimal("10000.00")  # 100 m² × 100.00
TOTAL_M2_VIGENTE = Decimal("15000.00")  # 100 m² × 150.00
AREA_M2 = 100.0

PORCENTAJE_PO_HISTORICO = Decimal("0.0020")
PORCENTAJE_PO_VIGENTE = Decimal("0.0010")

COSTO_VISITA_HISTORICO = Decimal("247.50")  # 0.05 × 4950
COSTO_VISITA_VIGENTE = Decimal("257.50")  # 0.05 × 5150


def _dec(valor) -> Decimal:
    """Normaliza un decimal de la API a `Decimal` (la API puede serializar texto o float)."""
    return Decimal(str(valor))


# ── Motor Por Metro Cuadrado ────────────────────────────────────────────────

@pytest.mark.django_db
def test_tarifas_vigentes_m2_con_fecha_usa_el_catalogo_historico(
    auth_client,
    m2_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 (100.00/m²) y el vigente (150.00/m²).
    WHEN:  se consultan las tarifas vigentes CON fecha efectiva.
    THEN:  la tarifa devuelta es la de esa fecha (100.00/m²) y su id es el de la
           tarifa histórica.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]

    response = auth_client.get(
        f"/liquidaciones/habilitacion-urbana/tarifas/vigentes?fecha={fecha.isoformat()}"
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    tarifa_vigente = result["tarifa_vigente"]["datos"]

    assert _dec(tarifa_vigente["costo_por_m2"]) == COSTO_M2_HISTORICO
    assert str(tarifa_vigente["id"]) == str(
        catalogo_legacy_historico["tarifa_m2_habilitacion_urbana"].id
    )


@pytest.mark.django_db
def test_tarifas_vigentes_m2_sin_fecha_conserva_el_comportamiento_vigente(
    auth_client,
    m2_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de 2023 y el vigente.
    WHEN:  se consultan las tarifas vigentes SIN fecha efectiva.
    THEN:  se devuelve la tarifa vigente de HOY — el comportamiento actual no
           cambia por la existencia de la fecha opcional.
    """
    response = auth_client.get("/liquidaciones/habilitacion-urbana/tarifas/vigentes")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    tarifa_vigente = result["tarifa_vigente"]["datos"]

    assert _dec(tarifa_vigente["costo_por_m2"]) == COSTO_M2_VIGENTE
    assert str(tarifa_vigente["id"]) == str(m2_base_setup["tarifa_m2_hu"].id)


@pytest.mark.django_db
def test_cotizar_m2_con_fecha_calcula_con_los_valores_de_esa_fecha(
    auth_client,
    m2_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: la ruta de cotización con fecha efectiva opcional.
    WHEN:  se cotiza con `?fecha=2023-06-15`.
    THEN:  el total se calcula con la tarifa de esa fecha, incluso si el payload
           trae la tarifa vigente: la fecha manda.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]

    for tarifa_id in (
        catalogo_legacy_historico["tarifa_m2_habilitacion_urbana"].id,
        m2_base_setup["tarifa_m2_hu"].id,
    ):
        payload = make_payload_m2_cotizar(
            tarifa_id,
            area_solicitada=AREA_M2,
        )
        response = auth_client.post(
            f"/liquidaciones/habilitacion-urbana/cotizar?fecha={fecha.isoformat()}",
            json=payload,
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.content}"
        )

        calculo = response.json()["data"]["calculo"]
        assert _dec(calculo["total"]) == TOTAL_M2_HISTORICO
        assert _dec(
            response.json()["data"]["datos"]["tarifa"]["costo_por_m2"]
        ) == COSTO_M2_HISTORICO


@pytest.mark.django_db
def test_cotizar_m2_sin_fecha_conserva_el_comportamiento_vigente(
    auth_client,
    m2_base_setup,
):
    """
    GIVEN: la ruta de cotización sin fecha efectiva.
    WHEN:  se cotiza sin `fecha`.
    THEN:  el total se calcula con la tarifa vigente de HOY — sin cambios.
    """
    payload = make_payload_m2_cotizar(
        m2_base_setup["tarifa_m2_hu"].id,
        area_solicitada=AREA_M2,
    )
    response = auth_client.post("/liquidaciones/habilitacion-urbana/cotizar", json=payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert _dec(data["calculo"]["total"]) == TOTAL_M2_VIGENTE
    assert _dec(data["datos"]["tarifa"]["costo_por_m2"]) == COSTO_M2_VIGENTE


# ── Motor PorcentajeObra ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_tarifas_vigentes_po_con_fecha_usa_el_catalogo_historico(
    auth_client,
    po_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de Edificaciones (0.20 %) y el vigente (0.10 %).
    WHEN:  se consultan las tarifas vigentes CON fecha efectiva.
    THEN:  se devuelve la tarifa de esa fecha y las habilitadas de esa fecha.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]

    response = auth_client.get(
        f"/liquidaciones/edificaciones/tarifas/vigentes?fecha={fecha.isoformat()}"
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    assert len(result["tarifas"]) == 1
    assert _dec(result["tarifas"][0]["porcentaje_liquidacion"]) == PORCENTAJE_PO_HISTORICO
    assert str(result["tarifas"][0]["id"]) == str(
        catalogo_legacy_historico["tarifa_po_edificacion"].id
    )
    assert len(result["especialidades_disponibles"]) == 3


@pytest.mark.django_db
def test_tarifas_vigentes_po_sin_fecha_conserva_el_comportamiento_vigente(
    auth_client,
    po_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de Edificaciones y el vigente.
    WHEN:  se consultan las tarifas vigentes SIN fecha efectiva.
    THEN:  se devuelve la tarifa vigente de HOY — el comportamiento actual no
           cambia por la existencia de la fecha opcional.
    """
    response = auth_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    porcentajes = [_dec(t["porcentaje_liquidacion"]) for t in result["tarifas"]]

    assert PORCENTAJE_PO_VIGENTE in porcentajes
    assert PORCENTAJE_PO_HISTORICO not in porcentajes


# ── Motor Visitas ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_tarifas_vigentes_visitas_con_fecha_usa_el_catalogo_historico(
    auth_client,
    io_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de visitas (5 % de la UIT de 2023).
    WHEN:  se consultan las tarifas vigentes CON fecha efectiva.
    THEN:  el costo por visita se calcula con la UIT de esa fecha.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]

    response = auth_client.get(
        f"/liquidaciones/inspeccion-obra/tarifas/vigentes?fecha={fecha.isoformat()}"
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    assert len(result["tarifas"]) == 1
    assert _dec(result["tarifas"][0]["costo_por_visita"]) == COSTO_VISITA_HISTORICO


@pytest.mark.django_db
def test_tarifas_vigentes_visitas_sin_fecha_conserva_el_comportamiento_vigente(
    auth_client,
    io_base_setup,
    catalogo_legacy_historico,
):
    """
    GIVEN: el catálogo histórico de visitas y el vigente.
    WHEN:  se consultan las tarifas vigentes SIN fecha efectiva.
    THEN:  el costo por visita se calcula con la UIT vigente de HOY.
    """
    response = auth_client.get("/liquidaciones/inspeccion-obra/tarifas/vigentes")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    result = response.json()["data"]
    assert len(result["tarifas"]) == 1
    assert _dec(result["tarifas"][0]["costo_por_visita"]) == COSTO_VISITA_VIGENTE
