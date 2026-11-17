"""
Integration tests for the EDICIÓN de una IO con continuidad de visitas
(change `io-continuidad-visitas-ui-edit`, Fase 1 — backend).

Cubre el contrato funcional del discriminador de modo del PATCH de IO:

- `activar`   → crea la fila `LiquidacionContinuidadVisitas` de B y la cabecera
                pasa a cobrar la DIFERENCIA (valor completo − crédito).
- `mantener`  → actualiza el registro de continuidad (crédito, pendientes,
                referencia a A, observación) y reaplica la diferencia.
- `desactivar`→ elimina la fila y RESTAURA los montos normales de B (valor
                completo del trabajo).
- Matriz de transición inválida → 400.
- Guard 409 (RH mensual / `DetalleHonorarioInspector` / `RegistroPagoInspector`)
  ANTES de cualquier escritura: "no se escribe nada".
- D9 (diferido a propósito): el guard NO se extiende a las ediciones de B sin
  operación de continuidad.
- D3: el crédito se deriva con el IGV HISTÓRICO de `fecha_registro`.

Estos tests NO se ejecutan en la fase de implementación (regla del usuario):
la ejecución queda diferida a la fase de verificación final.
"""
from datetime import date, datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.models.registro_pago_inspector import (
    RegistroPagoInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
    LiquidacionPorCategoriaVisitas,
)

# Los fixtures base de la IO (payload, previa, inspector) viven en el módulo
# hermano de la FASE 1 del cambio anterior: se importan para no duplicar la
# construcción del escenario (UIT 5150 · 5% → 257.50 por visita · IGV 18%).
from modules.liquidaciones.tests.integration.test_io_continuidad_visitas import (  # noqa: F401
    inspector_io,
    liquidacion_previa_io,
    payload_io,
)

# ── Constantes del escenario ──────────────────────────────────────────────
# UIT = 5150.00 · porcentaje_uit = 0.05 → costo por visita = 257.50
# IGV vigente = 18%
COSTO_POR_VISITA = Decimal("257.50")
IGV = Decimal("0.18")

# 4 visitas → 1030.00 netas · 1215.40 brutas
VALOR_COMPLETO_NETO = Decimal("1030.00")
VALOR_COMPLETO_BRUTO = Decimal("1215.40")

# 6 visitas → 1545.00 netas · 1823.10 brutas
VALOR_COMPLETO_NETO_6 = Decimal("1545.00")
VALOR_COMPLETO_BRUTO_6 = Decimal("1823.10")


# ── Helpers ───────────────────────────────────────────────────────────────


def _crear_io(auth_client, payload_io):
    """Crea una IO nueva (B) sin continuidad y devuelve (id, LCV)."""
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    assert created.status_code == 200, created.content
    data = created.json()["data"]
    lcv = LiquidacionPorCategoriaVisitas.objects.get(id=data["liquidacion_tipo"]["id"])
    return data["liquidacion_general"]["id"], lcv


def _crear_io_con_continuidad(auth_client, payload_io, liquidacion_previa_io):
    """Crea una IO nueva (B) CON continuidad (crédito 257.50) y devuelve (id, LCV)."""
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "257.50",
    }
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    assert created.status_code == 200, created.content
    data = created.json()["data"]
    lcv = LiquidacionPorCategoriaVisitas.objects.get(id=data["liquidacion_tipo"]["id"])
    return data["liquidacion_general"]["id"], lcv


def _patch_continuidad(auth_client, liquidacion_id, bloque, tipo_extra=None):
    """PATCH de la IO con el bloque de continuidad (y opcionalmente visitas)."""
    liquidacion_tipo = {"continuidad": bloque}
    if tipo_extra:
        liquidacion_tipo.update(tipo_extra)
    return auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={"liquidacion_tipo": liquidacion_tipo},
    )


# ── Contrato del schema de entrada ───────────────────────────────────────


def test_el_bloque_de_continuidad_acepta_el_discriminador_de_modo():
    """
    GIVEN: el wrapper del PATCH de IO.
    WHEN: se envía `liquidacion_tipo.continuidad` con `modo`.
    THEN: el modo se valida contra el discriminador (activar/mantener/desactivar)
          y el bloque es opcional (IO normal = comportamiento vigente).
    """
    from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_visitas_schemas import (
        LiquidacionPatchVisitasWrapperIn,
    )

    payload = {
        "liquidacion_tipo": {
            "continuidad": {
                "modo": "activar",
                "subtotal_credito": "257.50",
                "visitas_previas_pendientes": 1,
            }
        }
    }

    parsed = LiquidacionPatchVisitasWrapperIn(**payload)

    assert parsed.liquidacion_tipo.continuidad is not None
    assert parsed.liquidacion_tipo.continuidad.modo == "activar"
    assert parsed.liquidacion_tipo.continuidad.subtotal_credito == Decimal("257.50")

    # El bloque es opcional: una IO normal se valida igual que antes.
    sin_bloque = LiquidacionPatchVisitasWrapperIn(
        liquidacion_tipo={"datos": {"cantidad_visitas": 4}}
    )
    assert sin_bloque.liquidacion_tipo.continuidad is None


def test_un_modo_de_continuidad_desconocido_es_error_de_validacion():
    """
    GIVEN: un `modo` fuera del discriminador.
    THEN: la petición muere en la validación del schema (422), nunca llega al
          dominio.
    """
    import pydantic

    from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_visitas_schemas import (
        LiquidacionPatchVisitasWrapperIn,
    )

    with pytest.raises(pydantic.ValidationError):
        LiquidacionPatchVisitasWrapperIn(
            liquidacion_tipo={"continuidad": {"modo": "encender"}}
        )


# ── `activar` ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_patch_activar_crea_la_continuidad_y_cobra_la_diferencia(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO nueva (B) SIN continuidad (4 visitas → 1030.00 netas).
    WHEN: se PATCHea con `modo=activar` y un crédito neto de 257.50.
    THEN: se crea la fila de continuidad (monto_acumulado 1030.00 /
          total_acumulado 1215.40 / subtotal_credito 257.50 /
          total_credito 303.85) y la cabecera cobra la DIFERENCIA
          (772.50 / 911.55).
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "257.50",
        },
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    # La cabecera pasa de cobrar el valor completo a cobrar la diferencia.
    assert data["liquidacion_general"]["sub_total"] == 772.50
    assert data["liquidacion_general"]["total"] == 911.55

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad is not None
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40
    assert continuidad["subtotal_credito"] == 257.50
    # El total_credito lo deriva el servidor (257.50 × 1.18 = 303.85).
    assert continuidad["total_credito"] == 303.85
    assert continuidad["visitas_previas_pendientes"] == 1
    # El total de visitas de la previa lo deriva el servidor de la LCV de A.
    assert continuidad["visitas_previas_totales"] == 10
    assert continuidad["liquidacion_previa_id"] == str(
        liquidacion_previa_io["liquidacion"].id
    )

    # Persistencia: exactamente una fila, anclada a la LCV de B.
    assert LiquidacionContinuidadVisitas.objects.filter(liquidacion_visitas=lcv).count() == 1


@pytest.mark.django_db
def test_patch_activar_con_cambio_de_visitas_recalcula_el_valor_completo(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO nueva (B) SIN continuidad.
    WHEN: el mismo PATCH activa la continuidad Y cambia las visitas a 6.
    THEN: el valor completo se recalcula (1545.00 / 1823.10) y la diferencia
          se reaplica con el crédito (1287.50 / 1519.25).
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "257.50",
        },
        tipo_extra={"datos": {"cantidad_visitas": 6}},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_tipo"]["cantidad_visitas"] == 6
    assert data["liquidacion_general"]["sub_total"] == 1287.50
    assert data["liquidacion_general"]["total"] == 1519.25

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["monto_acumulado"] == 1545.00
    assert continuidad["total_acumulado"] == 1823.10
    assert continuidad["subtotal_credito"] == 257.50


# ── `mantener` ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_patch_mantener_actualiza_el_credito_y_reaplica_la_diferencia(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad (crédito 257.50 → diferencia 772.50).
    WHEN: se PATCHea con `modo=mantener` y un crédito neto de 515.00.
    THEN: el registro de continuidad actualiza el crédito (515.00 / 607.70) y
          la diferencia se reaplica (515.00 / 607.70).
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "mantener", "subtotal_credito": "515.00"},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    # 1030.00 − 515.00 = 515.00 ; 1215.40 − 607.70 = 607.70
    assert data["liquidacion_general"]["sub_total"] == 515.00
    assert data["liquidacion_general"]["total"] == 607.70

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["subtotal_credito"] == 515.00
    assert continuidad["total_credito"] == 607.70
    # El valor completo del trabajo no cambia: solo cambia a QUIÉN se le cobra.
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.subtotal_credito == Decimal("515.00")
    assert fila.total_credito == Decimal("607.70")


@pytest.mark.django_db
def test_patch_mantener_conserva_el_ancla_a_la_previa_cuando_se_omite(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad y referencia a la previa (A).
    WHEN: se PATCHea con `modo=mantener` y SOLO el modo (bloque sin campos).
    THEN: la referencia a A, el crédito y las visitas pendientes se conservan
          (replace por campo: lo omitido no se pierde) y la diferencia no cambia.
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client, liquidacion_id, {"modo": "mantener"}
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 772.50
    assert data["liquidacion_general"]["total"] == 911.55

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["liquidacion_previa_id"] == str(
        liquidacion_previa_io["liquidacion"].id
    )
    assert continuidad["subtotal_credito"] == 257.50
    assert continuidad["total_credito"] == 303.85
    assert continuidad["visitas_previas_pendientes"] == 1
    assert continuidad["visitas_previas_totales"] == 10

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.liquidacion_previa_id == liquidacion_previa_io["liquidacion"].id


# ── Bruto DECLARADO (`total_pagado_previa`) en el PATCH ──────────────────────
#
# El bruto pagado en la IO previa (IGV incluido) es la entrada autoritativa
# del crédito también en la EDICIÓN: lo declara el cliente y el servidor lo
# deriva con el IGV HISTÓRICO de `fecha_registro` (DD-5/DD-6).


@pytest.mark.django_db
def test_patch_activar_con_bruto_declarado_deriva_el_credito(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) SIN continuidad, 4 visitas (1030.00 netas).
    WHEN: se PATCHea con `modo=activar` y el bruto declarado (212.40).
    THEN: el crédito derivado (180.00 / 212.40) se persiste y la cabecera cobra
          la diferencia (850.00 / 1003.00).
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "activar", "total_pagado_previa": "212.40"},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 850.00
    assert data["liquidacion_general"]["total"] == 1003.00

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40
    assert continuidad["subtotal_credito"] == 180.00
    assert continuidad["total_credito"] == 212.40


@pytest.mark.django_db
def test_patch_mantener_con_bruto_declarado_re_deriva_el_credito(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) con continuidad creada por el camino legacy (crédito
           neto 257.50 → bruto 303.85).
    WHEN: se PATCHea con `modo=mantener` y el bruto declarado (212.40).
    THEN: el crédito se RE-DERIVA del bruto (180.00 / 212.40) y la cabecera
          cobra la diferencia (850.00 / 1003.00).
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "mantener", "total_pagado_previa": "212.40"},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 850.00
    assert data["liquidacion_general"]["total"] == 1003.00

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["subtotal_credito"] == 180.00
    assert continuidad["total_credito"] == 212.40

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.subtotal_credito == Decimal("180.00")
    assert fila.total_credito == Decimal("212.40")
    # El ancla a la previa NO se pierde por la re-derivación del crédito.
    assert fila.liquidacion_previa_id == liquidacion_previa_io["liquidacion"].id


@pytest.mark.django_db
def test_patch_mantener_sin_bruto_declarado_congela_el_credito(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) con continuidad creada por el camino legacy (crédito
           neto 257.50 → bruto 303.85).
    WHEN: se PATCHea con `modo=mantener` SIN bruto declarado.
    THEN: el crédito persistido queda CONGELADO (257.50 / 303.85): solo se
          reprecia el valor completo de B.
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "mantener"},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 772.50
    assert data["liquidacion_general"]["total"] == 911.55

    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.subtotal_credito == Decimal("257.50")
    assert fila.total_credito == Decimal("303.85")


@pytest.mark.django_db
def test_patch_desactivar_con_bruto_declarado_ignora_el_bloque(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad.
    WHEN: se PATCHea con `modo=desactivar` y un bruto declarado.
    THEN: el resto del bloque se IGNORA: la fila se elimina y la cabecera
          vuelve a cobrar el VALOR COMPLETO del trabajo.
    """
    liquidacion_id, _lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "desactivar", "total_pagado_previa": "212.40"},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1030.00
    assert data["liquidacion_general"]["total"] == 1215.40
    assert data["liquidacion_tipo"]["continuidad"] is None


@pytest.mark.django_db
def test_patch_sin_bloque_con_credito_mayor_al_valor_completo_devuelve_400(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    IV-5: el CRÉDITO no puede superar el VALOR COMPLETO del trabajo.

    GIVEN: una IO (B) con continuidad y un crédito mayor que el valor completo
           que queda al reducir las visitas.
    WHEN: se PATCHea SIN bloque de continuidad (solo se reprecia B).
    THEN: 400 (el MOTOR verifica el invariante antes de escribir) y NO se
          escribe nada: la cabecera conserva sus montos.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "900.00",
    }
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    assert created.status_code == 200, created.content
    liquidacion_id = created.json()["data"]["liquidacion_general"]["id"]

    lg_antes = LiquidacionGeneral.objects.get(id=liquidacion_id)
    sub_total_antes = lg_antes.sub_total

    # 1 visita → 257.50 netas: el crédito (900.00) supera el valor completo.
    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={"liquidacion_tipo": {"datos": {"cantidad_visitas": 1}}},
    )

    assert response.status_code == 400, response.content
    lg_antes.refresh_from_db()
    assert lg_antes.sub_total == sub_total_antes


@pytest.mark.django_db
def test_patch_mantener_con_cambio_de_visitas_congela_el_credito(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad (crédito 257.50).
    WHEN: el PATCH `modo=mantener` cambia las visitas a 6.
    THEN: el valor completo se recalcula (1545.00 / 1823.10) y el CRÉDITO
          queda congelado (257.50 / 303.85); la diferencia pasa a
          1287.50 / 1519.25.
    """
    liquidacion_id, _lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "mantener"},
        tipo_extra={"datos": {"cantidad_visitas": 6}},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1287.50
    assert data["liquidacion_general"]["total"] == 1519.25

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["monto_acumulado"] == 1545.00
    assert continuidad["total_acumulado"] == 1823.10
    assert continuidad["subtotal_credito"] == 257.50
    assert continuidad["total_credito"] == 303.85


# ── `desactivar` ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_patch_desactivar_elimina_la_fila_y_restaura_el_valor_completo(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad (4 visitas → diferencia 772.50).
    WHEN: se PATCHea con `modo=desactivar`.
    THEN: la fila de continuidad se elimina y la cabecera vuelve a cobrar el
          VALOR COMPLETO del trabajo (1030.00 / 1215.40).
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client, liquidacion_id, {"modo": "desactivar"}
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1030.00
    assert data["liquidacion_general"]["total"] == 1215.40
    assert data["liquidacion_tipo"]["continuidad"] is None

    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()


@pytest.mark.django_db
def test_patch_desactivar_con_cambio_de_visitas_restaura_el_valor_completo_actual(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON continuidad (4 visitas).
    WHEN: el PATCH `modo=desactivar` sube las visitas a 6.
    THEN: la cabecera cobra el valor completo ACTUAL (1545.00 / 1823.10): el
          apagado restaura los montos normales de B con el reprecio de B.
    """
    liquidacion_id, _lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "desactivar"},
        tipo_extra={"datos": {"cantidad_visitas": 6}},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1545.00
    assert data["liquidacion_general"]["total"] == 1823.10
    assert data["liquidacion_tipo"]["continuidad"] is None


# ── Matriz de transición inválida (400) ───────────────────────────────────


@pytest.mark.django_db
def test_patch_mantener_sin_continuidad_devuelve_400(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) SIN fila de continuidad.
    WHEN: se PATCHea con `modo=mantener`.
    THEN: 400 — no hay nada que mantener (y no se escribe nada).
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "mantener", "subtotal_credito": "100.00"},
    )

    assert response.status_code == 400, response.content
    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.sub_total == Decimal("1030.00")


@pytest.mark.django_db
def test_patch_desactivar_sin_continuidad_devuelve_400(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) SIN fila de continuidad.
    WHEN: se PATCHea con `modo=desactivar`.
    THEN: 400 — no hay nada que apagar.
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client, liquidacion_id, {"modo": "desactivar"}
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_patch_activar_con_continuidad_devuelve_400(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) CON fila de continuidad.
    WHEN: se PATCHea con `modo=activar`.
    THEN: 400 — la continuidad ya está encendida.
    """
    liquidacion_id, lcv = _crear_io_con_continuidad(
        auth_client, payload_io, liquidacion_previa_io
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "subtotal_credito": "100.00",
        },
    )

    assert response.status_code == 400, response.content
    # La fila vigente no se toca.
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.subtotal_credito == Decimal("257.50")


# ── Guard 409 (RH mensual / pagos al inspector) ───────────────────────────


@pytest.mark.django_db
def test_patch_continuidad_con_rh_mensual_devuelve_409_y_no_escribe_nada(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) con `DetalleHonorarioInspector` (RH mensual emitido).
    WHEN: se PATCHea con una operación de continuidad (y un cambio de visitas).
    THEN: 409 y NO se escribe nada: ni la continuidad, ni las visitas, ni los
          montos de la cabecera.
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    DetalleHonorarioInspector.objects.create(
        liquidacion_por_categoria_visitas=lcv,
        inspecciones_liquidadas=4,
        costo_por_inspeccion=COSTO_POR_VISITA,
        monto_contribuido=VALOR_COMPLETO_NETO,
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "257.50",
        },
        tipo_extra={"datos": {"cantidad_visitas": 6}},
    )

    assert response.status_code == 409, response.content

    # "No se escribe nada": tampoco los cambios de visitas/tarifa que acompañen.
    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()
    lcv.refresh_from_db()
    assert lcv.cantidad_visitas == 4
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.sub_total == Decimal("1030.00")
    assert lg.total == Decimal("1215.40")


@pytest.mark.django_db
def test_patch_continuidad_con_pagos_al_inspector_devuelve_409(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) con `RegistroPagoInspector` (pagos ya registrados).
    WHEN: se PATCHea con una operación de continuidad.
    THEN: 409 — bajar las visitas dejaría el saldo del inspector en negativo.
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=lcv,
        periodo=2026,
        mes=11,
        inspecciones_pagadas=2,
    )

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "257.50",
        },
    )

    assert response.status_code == 409, response.content
    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()


@pytest.mark.django_db
def test_el_guard_de_rh_no_bloquea_las_ediciones_sin_continuidad(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) con `DetalleHonorarioInspector`.
    WHEN: se PATCHea SOLO el reprecio de B (sin bloque de continuidad).
    THEN: 200 — D9 queda diferido a propósito: el guard NO se extiende a las
          ediciones ordinarias de B (comportamiento vigente).
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    DetalleHonorarioInspector.objects.create(
        liquidacion_por_categoria_visitas=lcv,
        inspecciones_liquidadas=4,
        costo_por_inspeccion=COSTO_POR_VISITA,
        monto_contribuido=VALOR_COMPLETO_NETO,
    )

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={"liquidacion_tipo": {"datos": {"cantidad_visitas": 6}}},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    assert data["liquidacion_general"]["sub_total"] == 1545.00
    assert data["liquidacion_general"]["total"] == 1823.10


# ── Reglas de negocio del bloque (400) ────────────────────────────────────


@pytest.mark.django_db
def test_patch_activar_rechaza_credito_negativo(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: un bloque de continuidad con crédito neto negativo.
    THEN: 400 (regla de negocio; NO 422 — la no-negatividad no se valida en el
          schema de entrada).
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {"modo": "activar", "subtotal_credito": "-100.00"},
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_patch_activar_rechaza_previa_inexistente(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una referencia a una liquidación previa que no existe.
    THEN: 400 (la previa debe existir y ser de Inspección de Obra).
    """
    import uuid

    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(uuid.uuid4()),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "100.00",
        },
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_patch_activar_rechaza_pendientes_mayores_que_el_total(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: más visitas pendientes que las visitas totales de la previa.
    THEN: 400 — misma regla de negocio de la creación.
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 99,
            "subtotal_credito": "100.00",
        },
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_patch_activar_rechaza_la_propia_io_como_previa(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una referencia de continuidad que apunta a la propia IO que se edita.
    THEN: 400 — A no puede ser B.
    """
    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "100.00",
        },
    )

    assert response.status_code == 400, response.content


# ── D3: el crédito se deriva con el IGV histórico ─────────────────────────


@pytest.mark.django_db
def test_patch_activar_deriva_el_credito_con_el_igv_historico_de_fecha_registro(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO registrada con una fecha dentro de un periodo con OTRO IGV
           (10% en lugar del 18% vigente).
    WHEN: se activa la continuidad con un crédito neto de 100.00.
    THEN: el crédito y el valor acumulado se derivan con el IGV HISTÓRICO de
          `fecha_registro` (total_acumulado 1133.00, total_credito 110.00) y
          el documento cuadra al centavo (1023.00 = 1133.00 − 110.00).
    """
    from modules.finanzas.domain.models.impuestos import IGV

    IGV.objects.create(
        valor=Decimal("0.10"),
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )

    liquidacion_id, _lcv = _crear_io(auth_client, payload_io)

    # La IO queda registrada con una fecha dentro del periodo del IGV de 10%.
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lg.fecha_registro = timezone.make_aware(datetime(2025, 6, 15, 10, 0, 0))
    lg.save(update_fields=["fecha_registro"])

    response = _patch_continuidad(
        auth_client,
        liquidacion_id,
        {
            "modo": "activar",
            "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
            "visitas_previas_pendientes": 1,
            "subtotal_credito": "100.00",
        },
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    continuidad = data["liquidacion_tipo"]["continuidad"]
    # 4 visitas × 257.50 = 1030.00 ; IGV histórico 10% → 1133.00
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1133.00
    # El crédito usa el MISMO IGV: 100.00 × 1.10 = 110.00
    assert continuidad["total_credito"] == 110.00
    assert data["liquidacion_general"]["sub_total"] == 930.00
    assert data["liquidacion_general"]["total"] == 1023.00


# ── Regresión: el PATCH sin bloque de continuidad no cambia ───────────────


@pytest.mark.django_db
def test_patch_sin_bloque_de_continuidad_conserva_el_comportamiento_vigente(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO (B) SIN continuidad.
    WHEN: se PATCHea solo el reprecio de B (sin bloque de continuidad).
    THEN: la cabecera cobra el VALOR COMPLETO y NO se crea fila de
          continuidad (comportamiento vigente, bit a bit).
    """
    liquidacion_id, lcv = _crear_io(auth_client, payload_io)

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={"liquidacion_tipo": {"datos": {"cantidad_visitas": 6}}},
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1545.00
    assert data["liquidacion_general"]["total"] == 1823.10
    assert data["liquidacion_tipo"]["continuidad"] is None
    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()
