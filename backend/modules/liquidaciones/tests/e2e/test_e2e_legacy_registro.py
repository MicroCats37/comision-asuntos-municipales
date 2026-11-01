"""
E2E flow tests for the MANUAL LEGACY REGISTRATION (Phase 3, task 3.3).

The flow mimics the real frontend journey of the legacy form:

1. GET  /liquidaciones/{tipo}/tarifas/vigentes?fecha=...   → catálogo de esa fecha
2. POST /liquidaciones/{tipo}/cotizar?fecha=...              → preview con esa fecha
3. POST /liquidaciones/{tipo}/nueva-liquidacion/legacy        → registro manual
4. El registro creado tiene EXACTAMENTE las cifras del preview.

The parity between (2) and (4) is the core contract of the change: the quote
preview and the persisted record run the SAME engine with the SAME effective
date, so the operator sees the number he is about to persist.

Covered engines: PorcentajeObra (Edificaciones), Por Metro Cuadrado
(Habilitación Urbana) and Visitas (Inspección de Obra).

All payloads come from the pure builders of `tests/fixtures/factories.py`
(no inline payload dictionaries).

DB-backed (pytest-django + real ORM), no mocks, `ninja.testing.TestClient`.
NOT EXECUTED in this phase — Phase 5 is the only phase allowed to run tests.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_legacy_io,
    make_payload_legacy_m2,
    make_payload_legacy_po,
    make_payload_m2_cotizar,
    make_payload_po_cotizar_estrategia,
    make_payload_visitas_cotizar,
)


def _dec(valor) -> Decimal:
    """Normaliza un decimal de la API a `Decimal` (la API puede serializar texto o float)."""
    return Decimal(str(valor))


# ── Motor PorcentajeObra (Edificaciones) ────────────────────────────────────

@pytest.mark.django_db
def test_e2e_legacy_edificaciones_tarifas_cotizacion_y_registro(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un operador elige una fecha de registro histórica.
    WHEN:  consulta las tarifas de esa fecha, pide la cotización y registra la
           liquidación legacy con el número explícito.
    THEN:  la cotización y el registro persistido tienen las MISMAS cifras, y el
           registro queda marcado como legacy con su número y su fecha.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]
    fecha_query = fecha.isoformat()
    valor_declarado = 1000000.00
    numero = 6401

    # Step 1 — GET tarifas vigentes en la fecha efectiva
    tarifas_response = auth_client.get(
        f"/liquidaciones/edificaciones/tarifas/vigentes?fecha={fecha_query}"
    )
    assert tarifas_response.status_code == 200, (
        f"Expected 200, got {tarifas_response.status_code}: {tarifas_response.content}"
    )

    tarifas_data = tarifas_response.json()["data"]
    assert len(tarifas_data["tarifas"]) == 1
    assert len(tarifas_data["especialidades_disponibles"]) == 3

    tarifas_payload = [
        {
            "tarifa_porcentaje_obra_id": str(tarifas_data["tarifas"][0]["id"]),
            "especialidad_id": str(tarifas_data["especialidades_disponibles"][0]["id"]),
        }
    ]

    # Step 2 — POST cotización con la fecha efectiva
    cotizar_response = auth_client.post(
        f"/liquidaciones/edificaciones/cotizar?fecha={fecha_query}",
        json=make_payload_po_cotizar_estrategia(
            valor_declarado=valor_declarado,
            tarifas=tarifas_payload,
        ),
    )
    assert cotizar_response.status_code == 200, (
        f"Expected 200, got {cotizar_response.status_code}: {cotizar_response.content}"
    )

    cotizacion = cotizar_response.json()["data"]
    assert _dec(cotizacion["porcentaje_liquidacion"]) == Decimal("0.0020")
    assert len(cotizacion["detalles"]) == 1

    # Step 3 — POST registro manual legacy
    crear_response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/legacy",
        json=make_payload_legacy_po(
            municipalidad.id,
            municipalidad.distrito_id,
            numero=numero,
            fecha_registro=fecha,
            valor_declarado=valor_declarado,
            tarifas=tarifas_payload,
            expediente="EXP-E2E-LEGACY-EDIF-001",
            observacion="E2E registro legacy Edificaciones",
        ),
    )
    assert crear_response.status_code == 200, (
        f"Expected 200, got {crear_response.status_code}: {crear_response.content}"
    )

    # Step 4 — el registro tiene las mismas cifras que el preview
    data = crear_response.json()["data"]
    lg = data["liquidacion_general"]
    le = data["liquidacion_especifica"]

    assert lg["legacy"] is True
    assert lg["estado"] == "PENDIENTE"
    assert lg["fecha_registro"].startswith(fecha_query)
    assert le["numero"] == numero

    assert _dec(lg["sub_total"]) == _dec(cotizacion["total_subtotal"])
    assert _dec(lg["total"]) == _dec(cotizacion["total"])
    assert _dec(lg["total"]) == Decimal("2360.00")


# ── Motor Por Metro Cuadrado (Habilitación Urbana) ──────────────────────────

@pytest.mark.django_db
def test_e2e_legacy_habilitacion_urbana_tarifas_cotizacion_y_registro(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un operador elige una fecha de registro histórica en Habilitación Urbana.
    WHEN:  consulta las tarifas de esa fecha, pide la cotización y registra la
           liquidación legacy.
    THEN:  la cotización y el registro persistido tienen las MISMAS cifras.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]
    fecha_query = fecha.isoformat()
    area_solicitada = 100.0
    numero = 6402

    # Step 1 — GET tarifas vigentes en la fecha efectiva
    tarifas_response = auth_client.get(
        f"/liquidaciones/habilitacion-urbana/tarifas/vigentes?fecha={fecha_query}"
    )
    assert tarifas_response.status_code == 200, (
        f"Expected 200, got {tarifas_response.status_code}: {tarifas_response.content}"
    )

    tarifas_data = tarifas_response.json()["data"]
    tarifa_id = str(tarifas_data["tarifa_vigente"]["datos"]["id"])
    assert _dec(tarifas_data["tarifa_vigente"]["datos"]["costo_por_m2"]) == Decimal("100.0000")

    # Step 2 — POST cotización con la fecha efectiva
    cotizar_response = auth_client.post(
        f"/liquidaciones/habilitacion-urbana/cotizar?fecha={fecha_query}",
        json=make_payload_m2_cotizar(tarifa_id, area_solicitada=area_solicitada),
    )
    assert cotizar_response.status_code == 200, (
        f"Expected 200, got {cotizar_response.status_code}: {cotizar_response.content}"
    )

    cotizacion = cotizar_response.json()["data"]

    # Step 3 — POST registro manual legacy
    crear_response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy",
        json=make_payload_legacy_m2(
            municipalidad.id,
            municipalidad.distrito_id,
            tarifa_id,
            numero=numero,
            fecha_registro=fecha,
            area_solicitada=area_solicitada,
            expediente="EXP-E2E-LEGACY-HU-001",
            observacion="E2E registro legacy Habilitación Urbana",
        ),
    )
    assert crear_response.status_code == 200, (
        f"Expected 200, got {crear_response.status_code}: {crear_response.content}"
    )

    # Step 4 — paridad entre preview y registro
    data = crear_response.json()["data"]
    lg = data["liquidacion_general"]
    le = data["liquidacion_especifica"]

    assert lg["legacy"] is True
    assert lg["estado"] == "PENDIENTE"
    assert lg["fecha_registro"].startswith(fecha_query)
    assert le["numero"] == numero

    assert _dec(lg["sub_total"]) == _dec(cotizacion["calculo"]["subtotal"])
    assert _dec(lg["total"]) == _dec(cotizacion["calculo"]["total"])
    assert _dec(lg["total"]) == Decimal("10000.00")


# ── Motor Visitas (Inspección de Obra) ──────────────────────────────────────

@pytest.mark.django_db
def test_e2e_legacy_inspeccion_obra_tarifas_cotizacion_y_registro(
    auth_client,
    municipalidad,
    catalogo_legacy_historico,
):
    """
    GIVEN: un operador elige una fecha de registro histórica en Inspección de Obra.
    WHEN:  consulta las tarifas de esa fecha, pide la cotización y registra la
           liquidación legacy.
    THEN:  la cotización y el registro persistido tienen las MISMAS cifras, y el
           registro se crea SIN liquidación previa ni vínculo de inspector.
    """
    fecha = catalogo_legacy_historico["fecha_registro"]
    fecha_query = fecha.isoformat()
    cantidad_visitas = 3
    numero = 6403

    # Step 1 — GET tarifas vigentes en la fecha efectiva
    tarifas_response = auth_client.get(
        f"/liquidaciones/inspeccion-obra/tarifas/vigentes?fecha={fecha_query}"
    )
    assert tarifas_response.status_code == 200, (
        f"Expected 200, got {tarifas_response.status_code}: {tarifas_response.content}"
    )

    tarifas_data = tarifas_response.json()["data"]
    assert len(tarifas_data["tarifas"]) == 1
    tarifa_id = str(tarifas_data["tarifas"][0]["id"])
    assert _dec(tarifas_data["tarifas"][0]["costo_por_visita"]) == Decimal("247.50")

    # Step 2 — POST cotización con la fecha efectiva
    cotizar_response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/cotizar?fecha={fecha_query}",
        json=make_payload_visitas_cotizar(
            tarifa_id,
            cantidad_visitas=cantidad_visitas,
        ),
    )
    assert cotizar_response.status_code == 200, (
        f"Expected 200, got {cotizar_response.status_code}: {cotizar_response.content}"
    )

    cotizacion = cotizar_response.json()["data"]

    # Step 3 — POST registro manual legacy (sin liquidacion_previa_id ni inspector)
    crear_response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion/legacy",
        json=make_payload_legacy_io(
            municipalidad.id,
            municipalidad.distrito_id,
            tarifa_id,
            numero=numero,
            fecha_registro=fecha,
            cantidad_visitas=cantidad_visitas,
            expediente="EXP-E2E-LEGACY-IO-001",
            observacion="E2E registro legacy Inspección de Obra",
        ),
    )
    assert crear_response.status_code == 200, (
        f"Expected 200, got {crear_response.status_code}: {crear_response.content}"
    )

    # Step 4 — paridad entre preview y registro
    data = crear_response.json()["data"]
    lg = data["liquidacion_general"]
    le = data["liquidacion_especifica"]

    assert lg["legacy"] is True
    assert lg["estado"] == "PENDIENTE"
    assert lg["fecha_registro"].startswith(fecha_query)
    assert le["numero"] == numero

    assert _dec(lg["sub_total"]) == _dec(cotizacion["calculo"]["subtotal"])
    assert _dec(lg["total"]) == _dec(cotizacion["calculo"]["total"])
    assert _dec(lg["total"]) == Decimal("876.15")

    # El registro legacy de IO no tiene inspectores asociados.
    assert data["liquidacion_tipo"]["inspectores"] == []
