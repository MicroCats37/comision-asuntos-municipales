"""
Tests de API de la cotización de IO por MODO (NORMAL | CONTINUAR).

Cubre el bloque B + C-1/C-2 de la exploración `io-continuity-server-quote`:
- CP-1  el payload vigente de `/cotizar` sigue siendo byte-compatible.
- CP-2  el payload vigente de `/cotizar-edicion` sigue siendo byte-compatible.
- CP-3  NORMAL con `continuidad` ⇒ 422.
- CP-4  `modo_cotizacion` desconocido ⇒ 422.
- CP-5  CONTINUAR sin `total_pagado_previa` ⇒ 422.
- CP-6  CONTINUAR con campos extra ⇒ 422.
- CP-7  CONTINUAR + `?fecha=` ⇒ 400 (no hay ruta de guardado legacy).
- CP-8  `total_pagado_previa` fuera de rango ⇒ 422.
- AS-1  NORMAL byte-compatible.
- AS-2  CONTINUAR con bloque autoritativo (y sin datos de la previa).
- AS-3  CONTINUAR en edición con el IGV HISTÓRICO.
- AS-4  validación de negocio (crédito mayor al valor completo ⇒ 400).

Base aritmética (fixtures compartidas): UIT 5150.00 · IGV 0.18 · 5 % UIT
→ 3 visitas = 772.50 neto · 911.55 bruto.
"""
from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.finanzas.domain.models.impuestos import IGV
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_io_cotizar,
    make_payload_io_cotizar_edicion,
)

RUTA_COTIZAR = "/liquidaciones/inspeccion-obra/cotizar"

NETO_ESPERADO = Decimal("772.50")
BRUTO_ESPERADO = Decimal("911.55")
BRUTO_DECLARADO = Decimal("212.40")
CREDITO_NETO_ESPERADO = Decimal("180.00")
CREDITO_BRUTO_ESPERADO = Decimal("212.40")
DIFERENCIA_NETA_ESPERADA = Decimal("592.50")
DIFERENCIA_BRUTA_ESPERADA = Decimal("699.15")


def _monto(valor):
    """Lee un importe del JSON (número o string) como Decimal comparable."""
    return Decimal(str(valor))


# ── AS-1 / CP-1: NORMAL byte-compatible ───────────────────────────────────────


@pytest.mark.django_db
def test_cotizar_io_payload_vigente_sigue_siendo_byte_compatible(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-1: el payload VIGENTE (sin `modo_cotizacion`) valida y devuelve las
    MISMAS cifras de `calculo`, con `modo_cotizacion == "NORMAL"` y
    `continuidad == null`.
    """
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(tarifa_visitas_io.id, cantidad_visitas=3),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["modo_cotizacion"] == "NORMAL"
    assert data["continuidad"] is None
    # Las cifras NO se mueven: son las mismas del payload vigente.
    assert _monto(data["calculo"]["subtotal"]) == NETO_ESPERADO
    assert _monto(data["calculo"]["total"]) == BRUTO_ESPERADO
    assert _monto(data["calculo"]["monto_bruto"]) == NETO_ESPERADO
    # Serialización heredada (Decimal como string) preservada byte a byte.
    assert data["calculo"]["subtotal"] == "772.5000"
    assert data["calculo"]["total"] == "911.550000"
    assert data["datos"]["entrada"]["datos"]["cantidad_visitas"] == 3
    assert data["datos"]["entrada"]["datos"]["categoria"] == "INSPECCION"


@pytest.mark.django_db
def test_cotizar_io_modo_normal_explicito_es_equivalente_al_payload_vigente(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-1: declarar `modo_cotizacion: "NORMAL"` no cambia ninguna cifra."""
    payload = make_payload_io_cotizar(tarifa_visitas_io.id, cantidad_visitas=3)
    payload["liquidacion_especifica"]["modo_cotizacion"] = "NORMAL"

    response = auth_client.post(RUTA_COTIZAR, json=payload)

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    assert data["modo_cotizacion"] == "NORMAL"
    assert _monto(data["calculo"]["total"]) == BRUTO_ESPERADO


# ── AS-2: CONTINUAR con bloque autoritativo ───────────────────────────────────


@pytest.mark.django_db
def test_cotizar_io_continuar_devuelve_las_cifras_autoritativas(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-2: el modo CONTINUAR devuelve las 8 cifras autoritativas y `calculo`
    lleva el VALOR COMPLETO de B.
    """
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=BRUTO_DECLARADO,
        ),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["modo_cotizacion"] == "CONTINUAR"
    continuidad = data["continuidad"]
    assert _monto(continuidad["total_pagado_previa"]) == BRUTO_DECLARADO
    assert _monto(continuidad["valor_completo_neto"]) == NETO_ESPERADO
    assert _monto(continuidad["valor_completo_bruto"]) == BRUTO_ESPERADO
    assert _monto(continuidad["credito_neto"]) == CREDITO_NETO_ESPERADO
    assert _monto(continuidad["credito_bruto"]) == CREDITO_BRUTO_ESPERADO
    assert _monto(continuidad["diferencia_neto"]) == DIFERENCIA_NETA_ESPERADA
    assert _monto(continuidad["diferencia_bruto"]) == DIFERENCIA_BRUTA_ESPERADA
    assert _monto(continuidad["igv_porcentaje"]) == Decimal("0.18")

    # Consistencia interna: `calculo` == valor completo de B.
    assert _monto(data["calculo"]["total"]) == _monto(continuidad["valor_completo_bruto"])
    assert _monto(data["calculo"]["subtotal"]) == _monto(continuidad["valor_completo_neto"])


@pytest.mark.django_db
def test_cotizar_io_continuar_no_expone_datos_de_la_liquidacion_previa(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-2 (seguridad): la ruta de cotización NO desreferencia la liquidación
    previa: el bruto es una DECLARACIÓN del cliente y la respuesta no
    contiene ningún dato de una IO ajena.
    """
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=BRUTO_DECLARADO,
        ),
    )

    assert response.status_code == 200, response.content
    crudo = response.content.decode()
    assert "liquidacion_previa_id" not in crudo
    assert "liquidacion_previa" not in crudo


# ── AS-4 / CP-3..CP-8: validación de la API ───────────────────────────────────


@pytest.mark.django_db
def test_cotizar_io_rechaza_continuidad_en_modo_normal(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-3: NORMAL con `continuidad` es un payload mixto ⇒ 422."""
    payload = make_payload_io_cotizar(tarifa_visitas_io.id, cantidad_visitas=3)
    payload["liquidacion_especifica"]["modo_cotizacion"] = "NORMAL"
    payload["liquidacion_especifica"]["continuidad"] = {
        "total_pagado_previa": float(BRUTO_DECLARADO),
    }

    response = auth_client.post(RUTA_COTIZAR, json=payload)

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_rechaza_modo_desconocido(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-4: un `modo_cotizacion` desconocido ⇒ 422."""
    payload = make_payload_io_cotizar(tarifa_visitas_io.id, cantidad_visitas=3)
    payload["liquidacion_especifica"]["modo_cotizacion"] = "OTRO"

    response = auth_client.post(RUTA_COTIZAR, json=payload)

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_continuar_exige_total_pagado_previa(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-5: CONTINUAR sin el bloque `continuidad` ⇒ 422."""
    payload = make_payload_io_cotizar(tarifa_visitas_io.id, cantidad_visitas=3)
    payload["liquidacion_especifica"]["modo_cotizacion"] = "CONTINUAR"

    response = auth_client.post(RUTA_COTIZAR, json=payload)

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_continuar_rechaza_campos_extra(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-6: CONTINUAR con un campo desconocido ⇒ 422."""
    payload = make_payload_io_cotizar(
        tarifa_visitas_io.id,
        cantidad_visitas=3,
        modo="CONTINUAR",
        total_pagado_previa=BRUTO_DECLARADO,
    )
    payload["liquidacion_especifica"]["continuidad"]["liquidacion_previa_id"] = (
        "11111111-1111-1111-1111-111111111111"
    )

    response = auth_client.post(RUTA_COTIZAR, json=payload)

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_rechaza_bruto_no_positivo(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-8: `total_pagado_previa <= 0` ⇒ 422."""
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=Decimal("0"),
        ),
    )

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_rechaza_bruto_fuera_de_rango(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """CP-8: `total_pagado_previa > 9999999999.99` ⇒ 422."""
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=Decimal("10000000000.00"),
        ),
    )

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_cotizar_io_continuar_con_fecha_historica_devuelve_400(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    CP-7 / DD-10: CONTINUAR + `?fecha=` ⇒ 400. El alta legacy no admite
    bloque de continuidad: no hay ruta de guardado counterpart para la fecha
    histórica.
    """
    response = auth_client.post(
        f"{RUTA_COTIZAR}?fecha=2024-01-01",
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=BRUTO_DECLARADO,
        ),
    )

    assert response.status_code == 400, response.content
    assert "continuidad" in response.content.decode().lower()


@pytest.mark.django_db
def test_cotizar_io_continuar_rechaza_credito_mayor_al_valor_completo(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    AS-4: el crédito NO puede superar el valor completo del trabajo ⇒ 400
    (invariante IV-5 del servidor).
    """
    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=Decimal("5000.00"),
        ),
    )

    assert response.status_code == 400, response.content
    assert "crédito" in response.content.decode().lower() or "credito" in response.content.decode().lower()


@pytest.mark.django_db
def test_cotizar_io_continuar_no_escribe_nada_en_la_base_de_datos(
    auth_client,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """AS-4: la cotización es de solo lectura: no persiste ninguna fila."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
        LiquidacionContinuidadVisitas,
    )

    antes_general = LiquidacionGeneral.objects.count()
    antes_continuidad = LiquidacionContinuidadVisitas.objects.count()

    response = auth_client.post(
        RUTA_COTIZAR,
        json=make_payload_io_cotizar(
            tarifa_visitas_io.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=BRUTO_DECLARADO,
        ),
    )

    assert response.status_code == 200, response.content
    assert LiquidacionGeneral.objects.count() == antes_general
    assert LiquidacionContinuidadVisitas.objects.count() == antes_continuidad


# ── AS-3: CONTINUAR en edición con el IGV histórico ──────────────────────────


@pytest.fixture
def igv_vigente_020(db):
    """IGV vigente DISTINTO del histórico (0.20) para hacer observable el IGV usado."""
    return IGV.objects.create(
        valor=Decimal("0.20"),
        periodo_inicio=datetime(2024, 1, 1).date(),
        periodo_fin=None,
    )


@pytest.fixture
def io_historica_cotizable(
    db,
    municipalidad,
    proyecto,
    create_user,
    tipo_inspeccion_obra,
    igv_historico_2023,
    uit_historico_2023,
    igv_vigente_020,
    tarifa_visitas_historica_inspeccion_obra,
):
    """IO registrada en 2023 (IGV histórico 0.18, UIT histórica 4950)."""
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-COTZ-IO-MODOS-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("742.50"),
        total=Decimal("876.15"),
        fecha_registro=timezone.make_aware(datetime(2023, 6, 15)),
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)
    LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_historica_inspeccion_obra,
    )

    return lg


@pytest.mark.django_db
def test_cotizar_edicion_io_continuar_usa_el_igv_historico(
    auth_client,
    io_historica_cotizable,
    tarifa_visitas_historica_inspeccion_obra,
):
    """
    AS-3: la cotización de EDICIÓN usa el IGV HISTÓRICO de `fecha_registro`
    (0.18), no el vigente (0.20): es el mismo que usará el PATCH.
    """
    liquidacion_id = io_historica_cotizable.id

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}/cotizar-edicion",
        json=make_payload_io_cotizar_edicion(
            tarifa_visitas_historica_inspeccion_obra.id,
            cantidad_visitas=3,
            modo="CONTINUAR",
            total_pagado_previa=BRUTO_DECLARADO,
        ),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["modo_cotizacion"] == "CONTINUAR"
    continuidad = data["continuidad"]
    assert _monto(continuidad["igv_porcentaje"]) == Decimal("0.18")

    # 3 × (0.05 × 4950) = 742.50 neto · 742.50 × 1.18 = 876.15 bruto
    assert _monto(continuidad["valor_completo_neto"]) == Decimal("742.50")
    assert _monto(continuidad["valor_completo_bruto"]) == Decimal("876.15")
    # 212.40 ÷ 1.18 = 180.00 · 876.15 − 212.40 = 663.75
    assert _monto(continuidad["credito_neto"]) == Decimal("180.00")
    assert _monto(continuidad["credito_bruto"]) == Decimal("212.40")
    assert _monto(continuidad["diferencia_neto"]) == Decimal("562.50")
    assert _monto(continuidad["diferencia_bruto"]) == Decimal("663.75")


@pytest.mark.django_db
def test_cotizar_edicion_io_payload_vigente_sigue_siendo_byte_compatible(
    auth_client,
    io_historica_cotizable,
    tarifa_visitas_historica_inspeccion_obra,
):
    """CP-2: el payload vigente de `/cotizar-edicion` conserva sus cifras."""
    liquidacion_id = io_historica_cotizable.id

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}/cotizar-edicion",
        json=make_payload_io_cotizar_edicion(
            tarifa_visitas_historica_inspeccion_obra.id,
            cantidad_visitas=3,
        ),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["modo_cotizacion"] == "NORMAL"
    assert data["continuidad"] is None
    assert _monto(data["calculo"]["subtotal"]) == Decimal("742.50")
    assert _monto(data["calculo"]["total"]) == Decimal("876.15")
