"""
Tests de EDICIÓN de las estrategias de cotización PO de Edificaciones.

Cubre el Module 5 del change `liquidacion-po-modos-cotizacion`:

- `cotizar-edicion` por estrategia: la MISMA union discriminado y el MISMO
  motor que el preview de creación y que el PATCH; NO persiste nada.
- Fecha efectiva: IGV, UIT y derechos se resuelven por
  `LiquidacionGeneral.fecha_registro.date()` (histórico), nunca por hoy.
- PATCH: transiciones 1→2→3 y 3→2→1 con las TRES estrategias; los detalles se
  reemplazan, los snapshots de estrategia se actualizan y la fila de
  acumulación se CREA / ACTUALIZA / ELIMINA según la diferencia (nada obsoleto
  sobrevive).
- Rollback: un cálculo inválido no deja detalles ni acumulación a medias.
- Guards preservados: MANUAL (edge) → 409, PAGADA → 409.
- Contrato `numero_revision` del agente concurrente preservado.
- `/nueva-revision` y `/relacionada` con estrategia.
- Contratos de Taludes / Impacto Vial intactos.

Tests DB-backed (pytest-django + ORM real, fixtures existentes). Sin mocks.
NO SE EJECUTAN en este módulo: toda la ejecución queda reservada para el Módulo 8.
"""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest

from modules.finanzas.domain.models.impuestos import IGV
from modules.liquidaciones.domain.constants import (
    EstadoLiquidacion,
    EstrategiaCotizacionPO,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_patch_po_estrategia,
    make_payload_po_cotizar_edicion_estrategia,
    make_payload_po_estrategia,
    make_payload_po_nueva_revision_estrategia,
    make_payload_po_relacionada_estrategia,
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
VALOR_DECLARADO = Decimal("1000000.00")
TOTAL_EXPLICITO = Decimal("177.00")
H_CATALOGO = 3                     # 3 especialidades habilitadas en el catálogo

CREAR_URL = "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision"
NUEVA_REVISION_URL = "/liquidaciones/edificaciones/nueva-revision"
RELACIONADA_URL = "/liquidaciones/edificaciones/relacionada"


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_po_unica_edificaciones(db, tipo_edificacion):
    """Una sola tarifa PO de Edificaciones con f = 0.05 % (modelo de tarifa única)."""
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=datetime(2024, 1, 1).date(),
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
        periodo_inicio=datetime(2024, 1, 1).date(),
        periodo_fin=None,
    )


@pytest.fixture
def igv_posterior(db):
    """IGV con vigencia posterior a la fecha de registro histórica (20 %)."""
    return IGV.objects.create(
        valor=Decimal("0.20"),
        periodo_inicio=datetime(2025, 1, 1).date(),
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


def _crear_primera_revision(auth_client, municipalidad, *, estrategia=None,
                             valor_declarado=VALOR_DECLARADO, total_explicito=None,
                             tarifas=None, expediente="EXP-EDIT-001"):
    """Crea una Edificación por la API y devuelve el id de la liquidación."""
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=estrategia,
        valor_declarado=float(valor_declarado),
        total_explicito=None if total_explicito is None else float(total_explicito),
        tarifas=tarifas,
        expediente=expediente,
    )
    response = auth_client.post(CREAR_URL, json=payload)
    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    return response.json()["data"]["liquidacion_general"]["id"]


@pytest.fixture
def liquidacion_historica(
    db, municipalidad, proyecto, create_user, tipo_edificacion,
    igv_vigente, uit_vigente, derecho_po_sin_rangos,
    tarifa_po_unica_edificaciones, especialidad_estructuras, especialidad_arquitectura,
    especialidades_disponibles_edificacion,
):
    """
    Edificación registrada el 2024-06-15 (IGV 18 %) en modo NORMAL_SELECCIONADAS.

    Permite comprobar que la edición resuelve IGV/UIT/derechos por la fecha de
    REGISTRO y no por hoy (donde el IGV vigente es otro).
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-HISTORICA-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        fecha_registro=datetime(2024, 6, 15, 10, 0, tzinfo=dt_timezone.utc),
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    po = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=VALOR_DECLARADO,
        porcentaje_liquidacion=Decimal("0.0010"),
        estrategia_cotizacion=NORMAL,
        count_habilitadas=H_CATALOGO,
        porcentaje_tarifa=F_TARIFA,
        tarifa_aplicada=tarifa_po_unica_edificaciones,
        derecho_minimo=Decimal("0.00"),
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0"),
        derecho_aplicado=derecho_po_sin_rangos,
    )

    for especialidad, subtotal in (
        (especialidad_estructuras, Decimal("500.00")),
        (especialidad_arquitectura, Decimal("500.00")),
    ):
        LiquidacionPorcentajeObraDetalle.objects.create(
            liquidacion_porcentaje=po,
            tarifa_aplicada=tarifa_po_unica_edificaciones,
            especialidad=especialidad,
            porcentaje_aplicado=F_TARIFA,
            subtotal=subtotal,
            importe_parcial=subtotal,
            ajuste_redondeo=Decimal("0.00"),
        )

    return lg


# ── cotizar-edicion: preview por estrategia ────────────────────────────────────

@pytest.mark.django_db
def test_cotizar_edicion_habilitadas_proyecta_acumulacion_sin_persistir(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  se pide el preview de edición en modo habilitadas-participantes.
    THEN:  el padre cobra H x f (0.15 %), el participante recibe 500.00 y la
           diferencia (1000.00 / 0.10 %) se proyecta como acumulación EFÍMERA.
    AND:   el preview NO persiste la acumulación.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert data["estrategia_cotizacion"] == HABILITADAS
    assert data["count_habilitadas"] == H_CATALOGO
    assert _dec(data["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("1500.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("1770.0"))
    assert len(data["detalles"]) == 1
    assert _dec(data["detalles"][0]["subtotal"]) == pytest.approx(Decimal("500.0"))

    acumulacion = data["acumulacion"]
    assert acumulacion is not None
    assert _dec(acumulacion["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(acumulacion["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))

    # El preview NUNCA persiste.
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0
    assert LiquidacionPorcentajeObra.objects.get().estrategia_cotizacion == NORMAL


@pytest.mark.django_db
def test_cotizar_edicion_total_explicito_extrae_subtotal_igv_y_cuota(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  se pide el preview de edición en modo total explícito (177.00).
    THEN:  el subtotal es 150.00, el total se conserva en 177.00, la cuota del
           participante es 50.00 y la acumulación (100.00) NO tiene porcentaje.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion=TOTAL,
            valor_declarado=float(VALOR_DECLARADO),
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert data["estrategia_cotizacion"] == TOTAL
    assert _dec(data["total_explicito"]) == pytest.approx(Decimal("177.0"))
    assert _dec(data["valor_declarado"]) == pytest.approx(VALOR_DECLARADO)
    assert data["porcentaje_liquidacion"] is None
    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("150.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("177.0"))
    assert _dec(data["detalles"][0]["subtotal"]) == pytest.approx(Decimal("50.0"))
    assert data["detalles"][0]["porcentaje_aplicado"] is None
    assert _dec(data["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("100.0"))
    assert data["acumulacion"]["porcentaje_acumulado"] is None


@pytest.mark.django_db
def test_cotizar_edicion_rechaza_estrategia_no_soportada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación existente.
    WHEN:  el preview de edición declara una cuarta estrategia inventada.
    THEN:  422 — no hay cuarto modo ni alias.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion="SUBASTA_POR_PARTICIPANTE",
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_cotizar_edicion_total_acepta_valor_informativo(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación existente.
    WHEN:  el preview declara el valor informativo y el total explícito.
    THEN:  200 — ambos viajan, pero el total sigue siendo autoritativo.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    payload = make_payload_po_cotizar_edicion_estrategia(
        estrategia_cotizacion=TOTAL,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    payload["liquidacion_tipo"]["datos"]["valor_declarado"] = float(VALOR_DECLARADO)

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    assert _dec(response.json()["data"]["valor_declarado"]) == pytest.approx(
        VALOR_DECLARADO
    )


@pytest.mark.django_db
def test_cotizar_edicion_no_persiste_nada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal con 1 detalle.
    WHEN:  se pide el preview de edición en modo habilitadas-participantes.
    THEN:  ni el padre, ni los detalles, ni la acumulación cambian.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    po_antes = LiquidacionPorcentajeObra.objects.get()
    detalles_antes = po_antes.detalles.count()

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    po_antes.refresh_from_db()
    assert po_antes.estrategia_cotizacion == NORMAL
    assert po_antes.detalles.count() == detalles_antes
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_cotizar_edicion_usa_la_fecha_de_registro_para_el_igv(
    auth_client, liquidacion_historica, igv_posterior,
    tarifa_po_unica_edificaciones, especialidad_estructuras,
):
    """
    GIVEN: una Edificación registrada el 2024-06-15 (IGV 18 %) con un IGV del
           20 % vigente desde 2025.
    WHEN:  se pide el preview de edición.
    THEN:  usa el IGV histórico (18 %): el total es 1770.00 y no 1800.00.
    """
    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_historica.id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    data = response.json()["data"]

    assert _dec(data["total_subtotal"]) == pytest.approx(Decimal("1500.0"))
    assert _dec(data["total"]) == pytest.approx(Decimal("1770.0")), \
        "El preview debe usar el IGV de la fecha de registro (18 %), no el vigente"


# ── PATCH: persistencia, transiciones y ciclo de acumulación ────────────────────

@pytest.mark.django_db
def test_patch_normal_seleccionadas_persiste_estrategia_y_snapshots(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación creada en modo habilitadas-participantes.
    WHEN:  se hace PATCH a modo normal conservando el valor declarado.
    THEN:  el PO persiste la estrategia, H y el porcentaje de tarifa; el
           subtotal es n x f (500.00) y NO existe fila de acumulación.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=NORMAL,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == NORMAL
    assert tipo["count_habilitadas"] == H_CATALOGO
    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0005"))
    assert tipo["total_explicito"] is None
    assert tipo["acumulacion"] is None

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == NORMAL
    assert po.count_habilitadas == H_CATALOGO
    assert po.total_explicito is None
    assert po.detalles.count() == 1
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0

    lg = LiquidacionGeneral.objects.get()
    assert lg.sub_total == Decimal("500.00")
    assert lg.total == Decimal("590.00")


@pytest.mark.django_db
def test_patch_transicion_normal_a_habilitadas_crea_la_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal (1 participante, sin acumulación).
    WHEN:  se hace PATCH a modo habilitadas-participantes.
    THEN:  se CREA la fila de acumulación (1000.00 / 0.10 %) y el padre cobra
           H x f (invariante I-1: subtotal = detalles + acumulación).
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(tipo["acumulacion"]["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))

    fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
    assert fila.subtotal_acumulado == Decimal("1000.00")
    assert fila.porcentaje_acumulado == Decimal("0.0010")

    po = LiquidacionPorcentajeObra.objects.get()
    lg = LiquidacionGeneral.objects.get()
    suma_detalles = sum((d.subtotal for d in po.detalles.all()), Decimal("0"))
    assert lg.sub_total == suma_detalles + fila.subtotal_acumulado
    assert lg.sub_total == Decimal("1500.00")


@pytest.mark.django_db
def test_patch_transicion_habilitadas_a_normal_elimina_la_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes (con acumulación).
    WHEN:  se hace PATCH a modo normal.
    THEN:  la fila de acumulación se ELIMINA: no sobrevive una acumulación
           obsoleta de la estrategia anterior.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=NORMAL,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0, \
        "La acumulación de la estrategia anterior no puede sobrevivir"

    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == NORMAL
    assert po.porcentaje_liquidacion == Decimal("0.0005")
    assert po.detalles.count() == 1


@pytest.mark.django_db
def test_patch_transicion_a_total_explicito_persiste_porcentajes_null(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes.
    WHEN:  se hace PATCH a modo total explícito (177.00).
    THEN:  el total manda: padre y detalles sin porcentaje (invariante I-3), el
           valor declarado se conserva y la acumulación queda SIN porcentaje.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=TOTAL,
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

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
    assert po.total_explicito == Decimal("177.00")
    assert po.valor_declarado == VALOR_DECLARADO
    assert po.porcentaje_liquidacion is None
    assert all(d.porcentaje_aplicado is None for d in po.detalles.all())

    fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
    assert fila.subtotal_acumulado == Decimal("100.00")
    assert fila.porcentaje_acumulado is None

    lg = LiquidacionGeneral.objects.get()
    assert lg.sub_total == Decimal("150.00")
    assert lg.total == Decimal("177.00")


@pytest.mark.django_db
def test_patch_transicion_desde_total_preserva_valor_declarado(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo total explícito con valor declarado informativo.
    WHEN:  se hace PATCH a modo habilitadas-participantes sin valor declarado.
    THEN:  la transición reutiliza el valor declarado persistido.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=TOTAL,
        total_explicito=TOTAL_EXPLICITO,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.valor_declarado == VALOR_DECLARADO
    assert po.total_explicito is None


@pytest.mark.django_db
def test_patch_actualiza_valor_declarado_informativo_en_total_explicito(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  el PATCH declara el valor informativo y el total explícito.
    THEN:  ambos se persisten y el total sigue determinando las cifras.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=TOTAL,
            valor_declarado=2000000.0,
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == TOTAL
    assert po.valor_declarado == Decimal("2000000.00")
    assert po.total_explicito == TOTAL_EXPLICITO


@pytest.mark.django_db
def test_patch_rechaza_total_explicito_en_estrategia_de_valor_declarado(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes.
    WHEN:  el PATCH envía un total explícito sin cambiar de estrategia.
    THEN:  400 — el total explícito sólo aplica en TOTAL_EXPLICITO.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 400, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == HABILITADAS


@pytest.mark.django_db
def test_patch_revierte_el_cambio_si_el_calculo_falla(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_porcentaje_vigente,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal con piso UIT (515.00).
    WHEN:  el PATCH pide un total explícito cuyo subtotal (150.00) queda bajo ese
           piso.
    THEN:  400 y NADA cambia: la estrategia, los detalles y la acumulación
           quedan intactos (rollback).
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    po_antes = LiquidacionPorcentajeObra.objects.get()
    detalles_antes = list(
        po_antes.detalles.values_list("id", "subtotal", "porcentaje_aplicado")
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=TOTAL,
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 400, f"{response.status_code}: {response.content}"

    po_antes.refresh_from_db()
    assert po_antes.estrategia_cotizacion == NORMAL
    assert po_antes.total_explicito is None
    assert list(
        po_antes.detalles.values_list("id", "subtotal", "porcentaje_aplicado")
    ) == detalles_antes
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_patch_conserva_importe_parcial_y_ajuste_redondeo(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  se hace PATCH (cualquiera de las estrategias).
    THEN:  los detalles recreados conservan `importe_parcial` y `ajuste_redondeo`
           (los importes que leen los consumidores RH/CODEMU).
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    po = LiquidacionPorcentajeObra.objects.get()
    for detalle in po.detalles.all():
        assert detalle.importe_parcial is not None
        assert detalle.ajuste_redondeo is not None
        assert detalle.importe_parcial == detalle.subtotal


@pytest.mark.django_db
def test_patch_no_deja_detalles_obsoletos(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidad_arquitectura,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación con 2 participantes.
    WHEN:  se hace PATCH con un solo participante.
    THEN:  el detalle del participante retirado desaparece: no sobreviven
           detalles de la configuración anterior.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(
            tarifa_po_unica_edificaciones,
            especialidad_estructuras,
            especialidad_arquitectura,
        ),
    )
    assert LiquidacionPorcentajeObra.objects.get().detalles.count() == 2

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.detalles.count() == 1
    assert po.detalles.first().especialidad_id == especialidad_estructuras.id


@pytest.mark.django_db
def test_patch_con_todos_los_participantes_no_deja_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes con 1 participante.
    WHEN:  se hace PATCH con n == H (3 participantes).
    THEN:  la diferencia es cero y NO existe fila de acumulación (invariante I-5).
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(
                tarifa_po_unica_edificaciones,
                especialidad_estructuras,
                especialidad_arquitectura,
                especialidad_installaciones,
            ),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.detalles.count() == 3
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


# ── Matriz de transiciones 3x3 ──────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("origen", [NORMAL, HABILITADAS, TOTAL])
@pytest.mark.parametrize("destino", [NORMAL, HABILITADAS, TOTAL])
def test_patch_matriz_de_transiciones_3x3(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
    origen, destino,
):
    """
    GIVEN: una Edificación creada en la estrategia `origen`.
    WHEN:  se hace PATCH a la estrategia `destino`.
    THEN:  el estado persistido corresponde EXCLUSIVAMENTE a `destino`:
           snapshots propios de la estrategia, detalles sin porcentajes
           obsoletos y acumulación creada/actualizada/eliminada según la
           diferencia.
    """
    creation = {
        NORMAL: {"estrategia": NORMAL, "valor_declarado": VALOR_DECLARADO},
        HABILITADAS: {"estrategia": HABILITADAS, "valor_declarado": VALOR_DECLARADO},
        TOTAL: {"estrategia": TOTAL, "total_explicito": TOTAL_EXPLICITO},
    }[origen]

    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=creation["estrategia"],
        valor_declarado=creation.get("valor_declarado", VALOR_DECLARADO),
        total_explicito=creation.get("total_explicito"),
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        expediente=f"EXP-MATRIZ-{origen}-{destino}",
    )

    patch = {
        NORMAL: {"valor_declarado": float(VALOR_DECLARADO)},
        HABILITADAS: {"valor_declarado": float(VALOR_DECLARADO)},
        TOTAL: {"total_explicito": float(TOTAL_EXPLICITO)},
    }[destino]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=destino,
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
            **patch,
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == destino

    po = LiquidacionPorcentajeObra.objects.get()
    lg = LiquidacionGeneral.objects.get()
    assert po.estrategia_cotizacion == destino
    assert po.count_habilitadas == H_CATALOGO
    assert po.detalles.count() == 1, "No puede sobrevivir ningún detalle obsoleto"

    if destino == TOTAL:
        assert po.total_explicito == Decimal("177.00")
        assert po.valor_declarado == VALOR_DECLARADO
        assert po.porcentaje_liquidacion is None
        assert po.detalles.first().porcentaje_aplicado is None
        assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1
        fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
        assert fila.subtotal_acumulado == Decimal("100.00")
        assert fila.porcentaje_acumulado is None
        assert lg.sub_total == Decimal("150.00")
        assert lg.total == Decimal("177.00")
    else:
        assert po.total_explicito is None
        assert po.valor_declarado == VALOR_DECLARADO
        assert po.detalles.first().porcentaje_aplicado == F_TARIFA

        if destino == HABILITADAS:
            assert po.porcentaje_liquidacion == Decimal("0.0015")
            assert po.detalles.first().subtotal == Decimal("500.00")
            assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1
            fila = LiquidacionPorcentajeObraAcumulacion.objects.get()
            assert fila.subtotal_acumulado == Decimal("1000.00")
            assert fila.porcentaje_acumulado == Decimal("0.0010")
            assert lg.sub_total == Decimal("1500.00")
            assert lg.total == Decimal("1770.00")
        else:
            assert po.porcentaje_liquidacion == Decimal("0.0005")
            assert po.detalles.first().subtotal == Decimal("500.00")
            assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0
            assert lg.sub_total == Decimal("500.00")
            assert lg.total == Decimal("590.00")


# ── Guards y contrato de revisión ──────────────────────────────────────────────

@pytest.mark.django_db
def test_patch_de_una_liquidacion_manual_sigue_rechazado(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación creada en modo MANUAL (edge).
    WHEN:  se intenta un PATCH de cálculo.
    THEN:  409 — el guard del Module 1 se preserva (no es recalculable por
           tarifa) y no se escribe nada.
    """
    from modules.liquidaciones.tests.fixtures.factories import make_payload_po_edge

    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=1000.00,
    )
    response = auth_client.post("/liquidaciones/edificaciones/edge", json=payload)
    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    liquidacion_id = response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
        ),
    )

    assert response.status_code == 409, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == NORMAL
    assert po.detalles.count() == 3


@pytest.mark.django_db
def test_patch_de_una_liquidacion_pagada_sigue_rechazado(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en estado PAGADA.
    WHEN:  se intenta un PATCH de cálculo.
    THEN:  409 — el estado PAGADA bloquea toda la edición.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )
    lg = LiquidacionGeneral.objects.get()
    lg.estado = EstadoLiquidacion.PAGADA
    lg.save()

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 409, f"{response.status_code}: {response.content}"
    assert LiquidacionPorcentajeObra.objects.get().estrategia_cotizacion == NORMAL


@pytest.mark.django_db
def test_patch_conserva_el_numero_revision_si_se_omite(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en revisión 1.
    WHEN:  se hace PATCH de cálculo sin declarar `numero_revision`.
    THEN:  el número de revisión se conserva (1): el backend nunca lo deriva.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    lg = LiquidacionGeneral.objects.get()
    assert lg.numero_revision == 1


@pytest.mark.django_db
def test_patch_actualiza_el_numero_revision_en_el_mismo_boloque(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en revisión 1.
    WHEN:  el PATCH declara `numero_revision=3` y transiciona la estrategia.
    THEN:  ambos cambios se aplican de forma atómica: revisión 3 y estrategia
           habilitada-participantes con su acumulación.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            numero_revision=3,
            general_extra={"expediente": "EXP-PATCH-REV-003"},
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    lg = LiquidacionGeneral.objects.get()
    assert lg.numero_revision == 3
    assert lg.expediente == "EXP-PATCH-REV-003"
    assert LiquidacionPorcentajeObra.objects.get().estrategia_cotizacion == HABILITADAS
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1


@pytest.mark.django_db
def test_patch_con_numero_revision_invalido_no_escribe_nada(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en revisión 1.
    WHEN:  el PATCH declara un `numero_revision` fuera del conjunto permitido.
    THEN:  422 y NADA se escribe: ni la revisión ni la estrategia cambian.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            numero_revision=4,
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 422, f"{response.status_code}: {response.content}"
    lg = LiquidacionGeneral.objects.get()
    assert lg.numero_revision == 1
    assert LiquidacionPorcentajeObra.objects.get().estrategia_cotizacion == NORMAL
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_patch_solo_de_campos_generales_no_recalcula_la_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes con acumulación.
    WHEN:  se hace PATCH sólo de campos generales.
    THEN:  la estrategia, los detalles y la acumulación NO cambian: el bloque
           de cálculo no se toca si no se solicita.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            general_extra={"observacion": "Solo campos generales"},
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.detalles.count() == 1
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1
    assert LiquidacionGeneral.objects.get().observacion == "Solo campos generales"


@pytest.mark.django_db
def test_patch_preserva_la_estrategia_persistida_si_no_se_declara(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes.
    WHEN:  se hace PATCH sin declarar estrategia (sólo el valor declarado).
    THEN:  se recalcula con la estrategia PERSISTIDA: el padre sigue cobrando
           H x f y la acumulación se conserva.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    po = LiquidacionPorcentajeObra.objects.get()
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.porcentaje_liquidacion == Decimal("0.0015")
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 1


# ── Paridad preview / guardado ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_cotizar_edicion_y_patch_producen_las_mismas_cifras(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  se pide el preview de edición en modo habilitadas-participantes y
           luego se guarda ese mismo PATCH.
    THEN:  las cifras coinciden cifra por cifra: el preview y el guardado usan
           el MISMO motor.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    preview = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=make_payload_po_cotizar_edicion_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )
    assert preview.status_code == 200, f"{preview.status_code}: {preview.content}"
    preview_data = preview.json()["data"]

    guardado = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=make_patch_po_estrategia(
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )
    assert guardado.status_code == 200, f"{guardado.status_code}: {guardado.content}"
    tipo = guardado.json()["data"]["liquidacion_tipo"]

    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(_dec(preview_data["porcentaje_liquidacion"]))
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(_dec(preview_data["acumulacion"]["subtotal_acumulado"]))
    assert _dec(tipo["acumulacion"]["porcentaje_acumulado"]) == pytest.approx(_dec(preview_data["acumulacion"]["porcentaje_acumulado"]))

    po = LiquidacionPorcentajeObra.objects.get()
    lg = LiquidacionGeneral.objects.get()
    assert lg.sub_total == _dec(preview_data["total_subtotal"])
    assert lg.total == _dec(preview_data["total"])


# ── Nueva revision y relacionada ───────────────────────────────────────────────

@pytest.mark.django_db
def test_nueva_revision_hereda_la_estrategia_de_la_previa(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo habilitadas-participantes (con acumulación).
    WHEN:  se crea una nueva revisión sin declarar estrategia.
    THEN:  la revisión HEREDA la estrategia, recalcula sus snapshots con los
           valores de HOY y persiste su propia acumulación.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=HABILITADAS,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        NUEVA_REVISION_URL,
        json=make_payload_po_nueva_revision_estrategia(
            liquidacion_id,
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
            numero_revision=3,
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert tipo["count_habilitadas"] == H_CATALOGO
    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))

    po = LiquidacionPorcentajeObra.objects.get(
        liquidacion_general__id=response.json()["data"]["liquidacion_general"]["id"]
    )
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.detalles.count() == 1
    assert LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=po
    ).exists()


@pytest.mark.django_db
def test_nueva_revision_puede_cambiar_de_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación en modo normal.
    WHEN:  se crea una nueva revisión declarando total explícito.
    THEN:  la revisión usa la estrategia declarada: porcentajes NULL, total
           autoritativo y acumulación sin porcentaje.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        NUEVA_REVISION_URL,
        json=make_payload_po_nueva_revision_estrategia(
            liquidacion_id,
            estrategia_cotizacion=TOTAL,
            total_explicito=float(TOTAL_EXPLICITO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
            numero_revision=3,
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == TOTAL
    assert _dec(tipo["total_explicito"]) == pytest.approx(Decimal("177.0"))
    assert _dec(tipo["valor_declarado"]) == pytest.approx(VALOR_DECLARADO)
    assert tipo["porcentaje_liquidacion"] is None
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("100.0"))
    assert tipo["acumulacion"]["porcentaje_acumulado"] is None


@pytest.mark.django_db
def test_relacionada_acepta_la_estrategia_y_persiste_la_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_po_unica_edificaciones, derecho_po_sin_rangos,
    especialidad_estructuras, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una Edificación existente.
    WHEN:  se crea una relacionada en modo habilitadas-participantes.
    THEN:  la relacionada persiste su estrategia, sus snapshots y su fila de
           acumulación de forma atómica.
    """
    liquidacion_id = _crear_primera_revision(
        auth_client,
        municipalidad,
        estrategia=NORMAL,
        tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
    )

    response = auth_client.post(
        RELACIONADA_URL,
        json=make_payload_po_relacionada_estrategia(
            liquidacion_id,
            municipalidad_id=municipalidad.id,
            distrito_id=municipalidad.distrito_id,
            estrategia_cotizacion=HABILITADAS,
            valor_declarado=float(VALOR_DECLARADO),
            tarifas=_tarifas(tarifa_po_unica_edificaciones, especialidad_estructuras),
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert tipo["count_habilitadas"] == H_CATALOGO
    assert _dec(tipo["porcentaje_liquidacion"]) == pytest.approx(Decimal("0.0015"))
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(tipo["acumulacion"]["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))

    po = LiquidacionPorcentajeObra.objects.get(
        liquidacion_general__id=response.json()["data"]["liquidacion_general"]["id"]
    )
    assert po.estrategia_cotizacion == HABILITADAS
    assert po.detalles.count() == 1
    assert LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=po
    ).exists()


# ── Contratos de los demás motores: NO deben filtrarse campos de estrategia ─────

@pytest.mark.django_db
def test_taludes_conserva_su_contrato_en_el_patch(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes, derecho_porcentaje_vigente,
):
    """
    GIVEN: una liquidación de Taludes (motor PO que NO usa estrategias).
    WHEN:  se hace PATCH de cálculo.
    THEN:  200 con el mismo wrapper de siempre y SIN campos de estrategia PO:
           el camino legacy del servicio de patch queda intacto.
    """
    from modules.liquidaciones.tests.fixtures.factories import make_payload_po

    payload = make_payload_po(
        municipalidad.id,
        municipalidad.distrito_id,
        expediente="EXP-TALUDES-PATCH-001",
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
    liquidacion_id = response.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.patch(
        f"/liquidaciones/taludes/{liquidacion_id}",
        json=make_patch_po_estrategia(
            valor_declarado=2000000.00,
        ),
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert "estrategia_cotizacion" not in tipo
    assert "count_habilitadas" not in tipo
    assert "acumulacion" not in tipo
    assert _dec(tipo["valor_declarado"]) == pytest.approx(Decimal("2000000.0"))
