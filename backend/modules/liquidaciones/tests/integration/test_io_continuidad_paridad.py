"""
PARIDAD de la continuidad de visitas de IO: cotización ↔ alta ↔ PATCH.

Change `io-continuity-server-quote` (T-3 / AS-5). Es el test BLOQUEANTE del
lote 2: mientras el alta y el PATCH no consuman el MISMO resultado del MOTOR
que la cotización, la paridad `quote == persistido` es accidental.

Invariante de paridad (exploración §3.7):

    quote.continuidad.valor_completo_neto == persistido.monto_acumulado
    quote.continuidad.valor_completo_bruto == persistido.total_acumulado
    quote.continuidad.credito_neto        == persistido.subtotal_credito
    quote.continuidad.credito_bruto       == persistido.total_credito
    quote.continuidad.diferencia_neto     == cabecera.sub_total
    quote.continuidad.diferencia_bruto    == cabecera.total

Base aritmética (fixtures compartidas): UIT 5150.00 · IGV 0.18 · 5 % UIT
→ 257.50 por visita. 4 visitas → 1030.00 neto · 1215.40 bruto.
"""
from decimal import Decimal

import pytest

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_bloque_continuidad_io,
    make_payload_io_cotizar,
)

# Los fixtures base de la IO (payload, previa, inspector) viven en el módulo
# hermano del cambio `io-continuity-visitas-impacto`: se importan para no
# duplicar la construcción del escenario.
from modules.liquidaciones.tests.integration.test_io_continuidad_visitas import (  # noqa: F401
    inspector_io,
    liquidacion_previa_io,
    payload_io,
)

RUTA_COTIZAR = "/liquidaciones/inspeccion-obra/cotizar"

# 4 visitas × 257.50 → 1030.00 netas · 1030.00 × 1.18 = 1215.40 brutas
VALOR_COMPLETO_NETO = Decimal("1030.00")
VALOR_COMPLETO_BRUTO = Decimal("1215.40")

# BRUTO declarado por el cliente (IGV incluido)
BRUTO_DECLARADO = Decimal("212.40")
# 212.40 ÷ 1.18 = 180.00 · 180.00 × 1.18 = 212.40
CREDITO_NETO = Decimal("180.00")
CREDITO_BRUTO = Decimal("212.40")
# 1030.00 − 180.00 = 850.00 · 1215.40 − 212.40 = 1003.00
DIFERENCIA_NETA = Decimal("850.00")
DIFERENCIA_BRUTA = Decimal("1003.00")


def _monto(valor):
    """Lee un importe del JSON (número o string) como Decimal comparable."""
    return Decimal(str(valor))


def _cotizar(auth_client, tarifa_visitas_id, total_pagado_previa):
    """Cotiza en modo CONTINUAR y devuelve el bloque `continuidad` con Decimals."""
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_id,
            cantidad_visitas=4,
            modo="CONTINUAR",
            total_pagado_previa=total_pagado_previa,
        ),
    )
    assert response.status_code == 200, response.content
    bloque = response.json()["data"]["continuidad"]
    return {clave: _monto(valor) for clave, valor in bloque.items()}


def _crear_io_con_continuidad(auth_client, payload, liquidacion_previa_io, bloque):
    """Crea la IO (B) con el bloque de continuidad dado y devuelve (id, LCV)."""
    payload["liquidacion_especifica"]["continuidad"] = bloque
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload,
    )
    assert created.status_code == 200, created.content
    data = created.json()["data"]
    lcv = LiquidacionPorCategoriaVisitas.objects.get(id=data["liquidacion_tipo"]["id"])
    return data["liquidacion_general"]["id"], lcv


# ── AS-5: la paridad cotización ↔ alta ↔ PATCH ───────────────────────────────


@pytest.mark.django_db
def test_alta_con_bruto_declarado_persiste_exactamente_lo_cotizado(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-5 (alta): lo que se PERSISTE es exactamente lo que devolvió la
    cotización, cifra por cifra.

    GIVEN: una IO con 4 visitas y el bruto declarado 212.40.
    WHEN: se cotiza (CONTINUAR) y se crea la IO con el mismo bruto.
    THEN: la cabecera y la fila de continuidad coinciden con la cotización al
          céntavo.
    """
    bloque = make_bloque_continuidad_io(
        liquidacion_previa_id=liquidacion_previa_io["liquidacion"].id,
        total_pagado_previa=BRUTO_DECLARADO,
        visitas_previas_pendientes=1,
    )
    cotizacion = _cotizar(auth_client, tarifa_visitas_io.id, BRUTO_DECLARADO)

    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io, bloque
    )
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    cabecera = LiquidacionGeneral.objects.get(id=liquidacion_id)

    # ── Cabecera: la diferencia a cobrar ───────────────────────────────────
    assert cabecera.sub_total == DIFERENCIA_NETA
    assert cabecera.total == DIFERENCIA_BRUTA
    assert cabecera.sub_total == cotizacion["diferencia_neto"]
    assert cabecera.total == cotizacion["diferencia_bruto"]

    # ── Fila de continuidad: valor completo y crédito ──────────────────────
    assert fila.monto_acumulado == cotizacion["valor_completo_neto"]
    assert fila.total_acumulado == cotizacion["valor_completo_bruto"]
    assert fila.subtotal_credito == cotizacion["credito_neto"]
    assert fila.total_credito == cotizacion["credito_bruto"]

    assert fila.monto_acumulado == VALOR_COMPLETO_NETO
    assert fila.total_acumulado == VALOR_COMPLETO_BRUTO
    assert fila.subtotal_credito == CREDITO_NETO
    assert fila.total_credito == CREDITO_BRUTO


@pytest.mark.django_db
def test_patch_mantener_con_bruto_declarado_persiste_exactamente_lo_cotizado(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-5 (PATCH): el PATCH en modo `mantener` con el bruto declarado
    RE-DERIVA el crédito y persiste lo mismo que la cotización.

    GIVEN: una IO con continuidad ya encendida.
    WHEN: se PATCHea en modo `mantener` enviando el bruto declarado.
    THEN: el crédito y la diferencia persistidos son los de la cotización.
    """
    bloque_alta = make_bloque_continuidad_io(
        liquidacion_previa_id=liquidacion_previa_io["liquidacion"].id,
        total_pagado_previa=BRUTO_DECLARADO,
        visitas_previas_pendientes=1,
    )
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io, bloque_alta
    )

    cotizacion = _cotizar(auth_client, tarifa_visitas_io.id, BRUTO_DECLARADO)

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={
            "liquidacion_tipo": {
                "continuidad": make_bloque_continuidad_io(
                    modo="mantener",
                    total_pagado_previa=BRUTO_DECLARADO,
                )
            }
        },
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert _monto(data["liquidacion_general"]["sub_total"]) == cotizacion["diferencia_neto"]
    assert _monto(data["liquidacion_general"]["total"]) == cotizacion["diferencia_bruto"]

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.monto_acumulado == cotizacion["valor_completo_neto"]
    assert fila.total_acumulado == cotizacion["valor_completo_bruto"]
    assert fila.subtotal_credito == cotizacion["credito_neto"]
    assert fila.total_credito == cotizacion["credito_bruto"]


@pytest.mark.django_db
def test_paridad_completa_cotizacion_alta_y_patch_con_el_mismo_bruto(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-5 completo: los TRES caminos (cotizar, crear, editar) con el mismo
    bruto declarado producen EXACTAMENTE las mismas seis cifras.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    bloque_alta = make_bloque_continuidad_io(
        liquidacion_previa_id=liquidacion_previa_io["liquidacion"].id,
        total_pagado_previa=BRUTO_DECLARADO,
        visitas_previas_pendientes=1,
    )

    # (a) cotización
    cotizacion = _cotizar(auth_client, tarifa_visitas_io.id, BRUTO_DECLARADO)

    # (b) alta
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io, bloque_alta
    )
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    cabecera = LiquidacionGeneral.objects.get(id=liquidacion_id)

    # (c) PATCH `mantener`
    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={
            "liquidacion_tipo": {
                "continuidad": make_bloque_continuidad_io(
                    modo="mantener",
                    total_pagado_previa=BRUTO_DECLARADO,
                )
            }
        },
    )
    assert response.status_code == 200, response.content
    cabecera.refresh_from_db()
    fila.refresh_from_db()

    # ── Las SEIS igualdades de la exploración §3.7 ─────────────────────────
    assert fila.monto_acumulado == cotizacion["valor_completo_neto"]
    assert fila.total_acumulado == cotizacion["valor_completo_bruto"]
    assert fila.subtotal_credito == cotizacion["credito_neto"]
    assert fila.total_credito == cotizacion["credito_bruto"]
    assert cabecera.sub_total == cotizacion["diferencia_neto"]
    assert cabecera.total == cotizacion["diferencia_bruto"]

    # ── Y las cifras esperadas, sin ambigüedad ─────────────────────────────
    assert fila.monto_acumulado == VALOR_COMPLETO_NETO
    assert fila.total_acumulado == VALOR_COMPLETO_BRUTO
    assert fila.subtotal_credito == CREDITO_NETO
    assert fila.total_credito == CREDITO_BRUTO
    assert cabecera.sub_total == DIFERENCIA_NETA
    assert cabecera.total == DIFERENCIA_BRUTA


@pytest.mark.django_db
def test_el_bruto_declarado_manda_sobre_el_neto_enviado(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-7: si viaja el BRUTO declarado junto a un neto obsoleto, MANDA el
    bruto: el neto declarado se ignora.

    GIVEN: un bloque con `total_pagado_previa = 212.40` y
           `subtotal_credito = 999.00` (neto obsoleto).
    WHEN: se crea la IO.
    THEN: el crédito persistido es el derivado del bruto (180.00 / 212.40) y
          la cabecera cobra la diferencia contra el valor completo de B.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    bloque = make_bloque_continuidad_io(
        liquidacion_previa_id=liquidacion_previa_io["liquidacion"].id,
        total_pagado_previa=BRUTO_DECLARADO,
        subtotal_credito=Decimal("999.00"),
        visitas_previas_pendientes=1,
    )

    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io, bloque
    )

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    cabecera = LiquidacionGeneral.objects.get(id=liquidacion_id)

    assert fila.subtotal_credito == CREDITO_NETO
    assert fila.total_credito == CREDITO_BRUTO
    assert cabecera.sub_total == DIFERENCIA_NETA
    assert cabecera.total == DIFERENCIA_BRUTA


@pytest.mark.django_db
def test_el_monto_acumulado_no_se_mueve_al_activar_la_continuidad(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    CP-11 / R10: `monto_acumulado` es la BASE RH y no se mueve.

    GIVEN: una IO creada SIN continuidad (`sub_total` = valor completo).
    WHEN: se activa la continuidad con el bruto declarado.
    THEN: `monto_acumulado` = el mismo valor completo de antes y el
          `sub_total` pasa a ser la diferencia.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    assert created.status_code == 200, created.content
    liquidacion_id = created.json()["data"]["liquidacion_general"]["id"]

    cabecera = LiquidacionGeneral.objects.get(id=liquidacion_id)
    valor_completo = cabecera.sub_total
    assert valor_completo == VALOR_COMPLETO_NETO

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={
            "liquidacion_tipo": {
                "continuidad": make_bloque_continuidad_io(
                    modo="activar",
                    total_pagado_previa=BRUTO_DECLARADO,
                )
            }
        },
    )
    assert response.status_code == 200, response.content

    cabecera.refresh_from_db()
    lcv = LiquidacionPorCategoriaVisitas.objects.get(
        liquidacion_general=cabecera
    )
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)

    assert fila.monto_acumulado == valor_completo
    assert fila.total_acumulado == VALOR_COMPLETO_BRUTO
    assert cabecera.sub_total == DIFERENCIA_NETA
    assert cabecera.total == DIFERENCIA_BRUTA
