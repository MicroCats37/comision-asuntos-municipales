"""
Tests de API (create + preview) de las estrategias de cotización PO de Edificaciones.

Cubre el Module 4 del change `liquidacion-po-modos-cotizacion`:

- Preview `/cotizar` para las tres estrategias con el MISMO motor que la creación
  (paridad de cifras) y sin persistir nada.
- Union discriminado: se rechazan payloads mixtos, incompletos, con campos
  prohibidos y con estrategias no soportadas (no hay cuarto modo).
- Create (primera revisión): persiste estrategia, snapshots y detalles, y crea la
  fila de acumulación OneToOne según el resultado de la cotización.
- H se resuelve desde el catálogo de habilitadas, NUNCA desde los participantes.
- Contratos intactos de Taludes, Impacto Vial y edge (sin campos de estrategia PO).
- Rollback: un payload inválido no deja filas persistidas.

Tests DB-backed (pytest-django + ORM real, fixtures existentes). Sin mocks.
NO SE EJECUTAN en este módulo: toda la ejecución queda reservada para el Módulo 8.
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_po,
    make_payload_po_cotizar_estrategia,
    make_payload_po_edge,
    make_payload_po_estrategia,
)



# ── Helper de comparacion de decimales ───────────────────────────────────────

def _dec(valor) -> Decimal:
    """
    Normaliza un decimal de la API a `Decimal` para compararlo con exactitud.

    La API serializa los decimales como TEXTO (contrato `BaseSchema` +
    `success_response`); el frontend los coacciona a numero con
    `z.coerce.number()`. Las aserciones comparan contra `Decimal` para no
    depender de la representacion textual ni de la precision de `float`.
    """
    return Decimal(str(valor))


# ── Constantes de la aritmética ─────────────────────────────────────────────────

NORMAL = EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
HABILITADAS = EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES
TOTAL = EstrategiaCotizacionPO.TOTAL_EXPLICITO

F_TARIFA = Decimal("0.0005")        # 0.05 % — tarifa unitaria de Edificaciones
IGV = Decimal("0.18")              # 18 %
VALOR_DECLARADO = Decimal("1000000.00")
TOTAL_EXPLICITO = Decimal("177.00")
H_CATALOGO = 3                     # 3 especialidades habilitadas en el catálogo

COTIZAR_URL = "/liquidaciones/edificaciones/cotizar"
CREAR_URL = "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision"


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_po_unica_edificaciones(db, tipo_edificacion):
    """Una sola tarifa PO de Edificaciones con f = 0.05 % (modelo de tarifa única)."""
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base,
        porcentaje_liquidacion=F_TARIFA,
    )


@pytest.fixture
def derecho_po_sin_rangos(db):
    """Derecho vigente SIN piso UIT ni tope: aísla la aritmética de la estrategia."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_po_con_piso(db):
    """Derecho vigente con piso UIT = 5150 x 0.10 = 515.00 y sin tope."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _tarifas(tarifa, *especialidades):
    """Construye las entradas `tarifas[]` del payload a partir de una tarifa y especialidades."""
    return [
        {
            "tarifa_porcentaje_obra_id": str(tarifa.id),
            "especialidad_id": str(esp.id),
        }
        for esp in especialidades
    ]


# ── Preview: paridad con la creación y NO persistencia ─────────────────────────

@pytest.mark.django_db
def test_preview_normal_seleccionadas_conserva_el_contrato_vigente(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidad_arquitectura,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload de modo normal (sin discriminador) con 2 seleccionadas.
    WHEN:  se pide el preview.
    THEN:  devuelve 200 con la estrategia NORMAL_SELECCIONADAS, 2 detalles, sin
           acumulación, H del catálogo (3) y los totales esperados.
    AND:   el preview NO persiste ni el padre ni los detalles.
    """
    payload = make_payload_po_cotizar_estrategia(
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras, especialidad_arquitectura),
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert data["estrategia_cotizacion"] == NORMAL
    assert data["count_habilitadas"] == H_CATALOGO
    assert _dec(data["porcentaje_tarifa"]) == pytest.approx(Decimal("0.0005"))
    assert _dec(data["valor_declarado"]) == pytest.approx(Decimal("1000000.0"))
    assert _dec(data["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0010"))
    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("1180.0"))
    assert len(data["detalles"]) == 2
    assert data["acumulacion"] is None

    assert LiquidacionPorcentajeObra.objects.count() == 0
    assert LiquidacionGeneral.objects.count() == 0


@pytest.mark.django_db
def test_preview_tarifa_habilitadas_participantes_cobra_H_y_proyecta_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo habilitadas-participantes con 1 participante y H = 3 del catálogo.
    WHEN:  se pide el preview.
    THEN:  el padre cobra H x f (0.15 %), el participante recibe subtotal_padre/H
           (500.00) y la diferencia (1000.00 / 0.10 %) se proyecta como
           acumulación EFÍMERA.
    AND:   el preview NO persiste la acumulación.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=HABILITADAS,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert data["estrategia_cotizacion"] == HABILITADAS
    assert data["count_habilitadas"] == H_CATALOGO
    assert _dec(data["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("1500.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("1770.0"))

    assert len(data["detalles"]) == 1
    assert _dec(data["detalles"][0]["subtotal"]) == pytest.approx(Decimal("500.0"))
    assert _dec(data["detalles"][0]["porcentaje_aplicado"]) == pytest.approx(Decimal("0.0005"))

    acumulacion = data["acumulacion"]
    assert acumulacion is not None
    assert _dec(acumulacion["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(acumulacion["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))

    # El preview NUNCA persiste.
    assert LiquidacionPorcentajeObra.objects.count() == 0
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_preview_total_explicito_extrae_subtotal_igv_y_cuota(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo total explícito con total 177.00 (IGV 18 %) y 1 participante.
    WHEN:  se pide el preview.
    THEN:  el subtotal es 150.00, el IGV 27.00, el total se conserva en 177.00,
           la cuota del participante es 50.00 y la acumulación (100.00) NO tiene
           porcentaje (invariante I-3).
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=TOTAL,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert data["estrategia_cotizacion"] == TOTAL
    assert _dec(data["total_explicito"]) == pytest.approx(Decimal("177.0"))
    assert _dec(data["valor_declarado"]) == pytest.approx(VALOR_DECLARADO)
    assert data["porcentaje_liquidacion"] is None
    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("150.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("177.0"))

    assert len(data["detalles"]) == 1
    assert _dec(data["detalles"][0]["subtotal"]) == pytest.approx(Decimal("50.0"))
    assert data["detalles"][0]["porcentaje_aplicado"] is None

    acumulacion = data["acumulacion"]
    assert acumulacion is not None
    assert _dec(acumulacion["subtotal_acumulado"]) == pytest.approx(Decimal("100.0"))
    assert acumulacion["porcentaje_acumulado"] is None

    assert LiquidacionPorcentajeObra.objects.count() == 0


# ── Union discriminado: rechazo de payloads inválidos ──────────────────────────

@pytest.mark.django_db
def test_preview_rechaza_estrategia_no_soportada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload con una cuarta estrategia inventada.
    WHEN:  se pide el preview.
    THEN:  422 — no hay cuarto modo ni alias.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion="SUBASTA_POR_PARTICIPANTE",
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_preview_rechaza_campos_mixtos_de_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo normal que además envía `total_explicito` (campo de otra estrategia).
    WHEN:  se pide el preview.
    THEN:  422 — no se mezclan campos de estrategias.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=NORMAL,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        datos_extra={"total_explicito": 500.0},
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_preview_rechaza_valor_declarado_ausente_en_total_explicito(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo total explícito sin `valor_declarado`.
    WHEN:  se pide el preview.
    THEN:  422 — el valor informativo de la obra es obligatorio.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=TOTAL,
        valor_declarado=None,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_preview_rechaza_campo_obligatorio_ausente(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo total explícito sin `total_explicito`.
    WHEN:  se pide el preview.
    THEN:  422 — el campo obligatorio de la estrategia no puede faltar.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=TOTAL,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    # El factory con `valor_declarado` genera `datos.valor_declarado`: se sustituye
    # por `total_explicito` ausente para simular el payload incompleto.
    payload["liquidacion_especifica"]["datos"] = {}

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_preview_rechaza_count_habilitadas_enviado_por_el_cliente(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload que intenta fijar H desde el cliente.
    WHEN:  se pide el preview.
    THEN:  422 — H lo resuelve el catálogo, nunca el cliente.
    """
    payload = make_payload_po_cotizar_estrategia(
        estrategia_cotizacion=HABILITADAS,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    payload["liquidacion_especifica"]["count_habilitadas"] = 99

    response = auth_client.post(COTIZAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


# ── Create: persistencia de estrategia, snapshots y acumulación ─────────────────

@pytest.mark.django_db
def test_crear_normal_seleccionadas_persiste_estrategia_y_snapshots_sin_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidad_arquitectura,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una creación de Edificaciones en modo normal.
    WHEN:  se crea la primera revisión.
    THEN:  el PO persiste la estrategia, H y el porcentaje de tarifa; NO existe
           fila de acumulación (invariante I-4).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras, especialidad_arquitectura),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == NORMAL
    assert tipo["count_habilitadas"] == H_CATALOGO
    assert tipo["total_explicito"] is None
    assert _dec(tipo["porcentaje_tarifa"]) == pytest.approx(Decimal("0.0005"))
    assert tipo["acumulacion"] is None
    assert len(tipo["detalles"]) == 2

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == NORMAL
    assert po.count_habilitadas == H_CATALOGO
    assert po.total_explicito is None
    assert po.porcentaje_tarifa == F_TARIFA
    assert po.tarifa_aplicada_id == tarifa_po_unica_edificaciones.id
    assert po.detalles.count() == 2

    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_crear_tarifa_habilitadas_participantes_persiste_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una creación en modo habilitadas-participantes con 1 participante.
    WHEN:  se crea la primera revisión.
    THEN:  se persiste la estrategia, H = 3, un solo detalle (cuota 500.00) y la
           fila de acumulación (1000.00 / 0.10 %); el subtotal del padre conserva
           la suma de detalles + acumulación (invariante I-1).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=HABILITADAS,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert tipo["count_habilitadas"] == H_CATALOGO
    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert len(tipo["detalles"]) == 1
    assert _dec(tipo["detalles"][0]["subtotal"]) == pytest.approx(Decimal("500.0"))

    acumulacion = tipo["acumulacion"]
    assert acumulacion is not None
    assert _dec(acumulacion["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(acumulacion["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.count_habilitadas == H_CATALOGO
    assert po.detalles.count() == 1

    fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
    assert fila.liquidacion_porcentaje_id == po.id
    assert fila.subtotal_acumulado == Decimal("1000.00")
    assert fila.porcentaje_acumulado == Decimal("0.0010")

    # I-1: subtotal del padre == suma de detalles + acumulación
    lg = LiquidacionGeneral.objects.get()
    suma_detalles = sum((d.subtotal for d in po.detalles.all()), Decimal("0"))
    assert lg.sub_total == suma_detalles + fila.subtotal_acumulado
    assert lg.sub_total == Decimal("1500.00")


@pytest.mark.django_db
def test_crear_total_explicito_persiste_total_y_porcentajes_null(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una creación en modo total explícito (total 177.00).
    WHEN:  se crea la primera revisión.
    THEN:  el PO persiste el total explícito, los porcentajes quedan NULL
           (invariante I-3) y la acumulación se persiste SIN porcentaje.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == TOTAL
    assert _dec(tipo["total_explicito"]) == pytest.approx(Decimal("177.0"))
    assert _dec(tipo["valor_declarado"]) == pytest.approx(VALOR_DECLARADO)
    assert tipo["porcentaje_liquidacion"] is None
    assert tipo["detalles"][0]["porcentaje_aplicado"] is None
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("100.0"))
    assert tipo["acumulacion"]["porcentaje_acumulado"] is None

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == TOTAL
    assert po.total_explicito == Decimal("177.00")
    assert po.valor_declarado == VALOR_DECLARADO
    assert po.porcentaje_liquidacion is None
    assert all(d.porcentaje_aplicado is None for d in po.detalles.all())

    fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
    assert fila.subtotal_acumulado == Decimal("100.00")
    assert fila.porcentaje_acumulado is None

    lg = LiquidacionGeneral.objects.get()
    assert lg.total == Decimal("177.00")
    assert lg.sub_total == Decimal("150.00")


@pytest.mark.django_db
def test_crear_tarifa_habilitadas_con_todos_los_participantes_no_deja_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: modo habilitadas-participantes con n == H (3 participantes).
    WHEN:  se crea la primera revisión.
    THEN:  se crean 3 detalles y NO existe fila de acumulación (invariante I-5:
           la diferencia es cero).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=HABILITADAS,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(
            tarifa_po_unica_edificaciones,
            especialidad_estructuras,
            especialidad_arquitectura,
            especialidad_installaciones,
        ),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()

    assert po.detalles.count() == 3
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0

    lg = LiquidacionGeneral.objects.get()
    suma_detalles = sum((d.subtotal for d in po.detalles.all()), Decimal("0"))
    assert lg.sub_total == suma_detalles == Decimal("1500.00")


@pytest.mark.django_db
def test_crear_usa_H_del_catalogo_y_no_de_los_participantes(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: 1 participante pero 3 habilitadas en el catálogo.
    WHEN:  se crea la primera revisión en modo habilitadas-participantes.
    THEN:  el snapshot H vale 3 (el del catálogo) y la diferencia H − n = 2 se
           acumula: H NUNCA se deduce de los participantes.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=HABILITADAS,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()

    assert po.count_habilitadas == H_CATALOGO
    assert po.detalles.count() == 1

    fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
    assert fila.porcentaje_acumulado == Decimal("0.0010")
    assert fila.subtotal_acumulado == Decimal("1000.00")


# ── Paridad preview / save ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_preview_y_crear_producen_las_mismas_cifras(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: el mismo payload de modo habilitadas-participantes.
    WHEN:  se pide el preview y luego se crea la liquidación.
    THEN:  el preview y la respuesta de creación coinciden cifra por cifra: el
           preview y el guardado usan el MISMO motor.
    """
    tarifas = _tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras)

    preview = auth_client.post(
        COTIZAR_URL,
        json=make_payload_po_cotizar_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=tarifas,
        ),
    )
    assert preview.status_code == 200, f"{preview.status_code}: {preview.content}"
    preview_data = preview.json()["data"]

    creado = auth_client.post(
        CREAR_URL,
        json=make_payload_po_estrategia(
            municipalidad.id,
            municipalidad.distrito_id,
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=tarifas,
        ),
    )
    assert creado.status_code == 200, f"{creado.status_code}: {creado.content}"
    tipo = creado.json()["data"]["liquidacion_tipo"]

    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(_dec(preview_data["porcentaje_liquidacion"]))
    assert _dec(tipo["detalles"][0]["subtotal"]) == pytest.approx(_dec(preview_data["detalles"][0]["subtotal"]))
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(_dec(preview_data["acumulacion"]["subtotal_acumulado"]))
    assert _dec(tipo["acumulacion"]["porcentaje_acumulado"]) == pytest.approx(_dec(preview_data["acumulacion"]["porcentaje_acumulado"]))


# ── Rollback ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_con_total_explicito_fuera_de_derechos_no_persiste_nada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_con_piso,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un total explícito cuyo subtotal (150.00) queda bajo el piso UIT (515.00).
    WHEN:  se intenta crear la liquidación.
    THEN:  400 y NINGUNA fila queda persistida: la transacción del flujo se revierte.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 400, f"{response.status_code}: {response.content}"
    assert LiquidacionGeneral.objects.count() == 0
    assert LiquidacionPorcentajeObra.objects.count() == 0
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0
    assert Entidad.objects.count() == 0


@pytest.mark.django_db
def test_crear_con_payload_invalido_no_persiste_nada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una creación en modo total explícito sin `total_explicito`.
    WHEN:  se intenta crear la liquidación.
    THEN:  422 y NINGUNA fila queda persistida.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL,
        valor_declarado=float(VALOR_DECLARADO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    payload["liquidacion_especifica"]["datos"] = {}

    response = auth_client.post(CREAR_URL, json=payload)

    assert response.status_code == 422, f"{response.status_code}: {response.content}"
    assert LiquidacionGeneral.objects.count() == 0
    assert LiquidacionPorcentajeObra.objects.count() == 0
    assert Entidad.objects.count() == 0


# ── Contratos de los demás motores: NO deben filtrarse campos de estrategia ─────

@pytest.mark.django_db
def test_taludes_conserva_su_contrato_sin_campos_de_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes, derecho_porcentaje_vigente,
):
    """
    GIVEN: una creación de Taludes (motor PO que NO usa estrategias).
    WHEN:  se crea la primera revisión.
    THEN:  200 con el mismo wrapper de siempre y SIN campos de estrategia PO:
           la union de estrategias es exclusiva de Edificaciones.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-TALUDES-001",
        valor_declarado=1000000.00,
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_taludes.id),
                "especialidad_id": str(especialidad_taludes.id),
            }
        ],
    )

    response = auth_client.post(
        "/liquidaciones/taludes/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert "estrategia_cotizacion" not in tipo
    assert "count_habilitadas" not in tipo
    assert "acumulacion" not in tipo
    assert _dec(tipo["valor_declarado"]) == pytest.approx(Decimal("1000000.0"))
    assert len(tipo["detalles"]) == 1


@pytest.mark.django_db
def test_impacto_vial_conserva_su_contrato_sin_campos_de_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial, derecho_porcentaje_vigente,
):
    """
    GIVEN: una creación de Impacto Vial (motor PO que NO usa estrategias).
    WHEN:  se crea la primera revisión.
    THEN:  200 con el mismo wrapper de siempre y SIN campos de estrategia PO.
    """
    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-IV-001",
        valor_declarado=1000000.00,
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_iv.id),
                "especialidad_id": str(especialidad_impacto_vial.id),
            }
        ],
    )

    response = auth_client.post(
        "/liquidaciones/impacto-vial/nueva-liquidacion/primera-revision",
        json=payload,
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert "estrategia_cotizacion" not in tipo
    assert "count_habilitadas" not in tipo
    assert "acumulacion" not in tipo
    assert len(tipo["detalles"]) == 1


@pytest.mark.django_db
def test_edge_conserva_su_contrato_y_no_genera_acumulacion(
    auth_client, municipalidad, igv_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una creación edge (manual) de Edificaciones.
    WHEN:  se crea la liquidación edge.
    THEN:  200, la estrategia queda en NORMAL_SELECCIONADAS (valor por defecto) y
           NO existe fila de acumulación: el flujo edge no usa el motor de
           estrategias.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=1000.00,
    )

    response = auth_client.post("/liquidaciones/edificaciones/edge", json=payload)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == NORMAL
    assert tipo["acumulacion"] is None
    assert tipo["valor_declarado"] is None

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == NORMAL
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0
