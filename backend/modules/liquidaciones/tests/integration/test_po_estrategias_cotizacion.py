"""
Tests del motor único de cotización PO (estrategias de Edificaciones).

Cubre el Module 3 del change `liquidacion-po-modos-cotizacion`:

- Matriz 3x3: 3 estrategias × 3 escenarios de participación (n=1, n=H-1, n=H)
  con los invariantes normativos I-1..I-5.
- Aritmética por estrategia: NORMAL_SELECCIONADAS, TARIFA_HABILITADAS_PARTICIPANTES
  (padre H×f, cuota `subtotal_padre/H`) y TOTAL_EXPLICITO (extracción de IGV por
  resta, cuota `subtotal/H`, porcentajes NULL).
- Conservación de céntimos y determinismo del orden canónico (D-J).
- Derechos: rechazo por mínimo/máximo contra el subtotal previo al IGV, nunca
  elevación silenciosa del total explícito.
- Tasas históricas: el motor consume los valores YA resueltos por fecha efectiva.
- Proyección efímera: el motor no persiste padre, detalles ni acumulación.
- Fachada `calcular_cotizacion_po`: compatibilidad sin cambios de cifras.

Tests DB-backed (pytest-django + ORM real, fixtures existentes). Sin mocks.
NO SE EJECUTAN en este módulo: toda la ejecución queda reservada para el Módulo 8.
"""
from datetime import date
from decimal import Decimal

import pytest

from core.exceptions import BusinessError
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    CotizacionPOContexto,
    CotizacionPOEstrategiaData,
    DerechoPOCotizacion,
    LiquidacionPorcentajeObraCoreService,
)


# ── Constantes de la aritmética ─────────────────────────────────────────────────

NORMAL = EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
HABILITADAS = EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES
TOTAL = EstrategiaCotizacionPO.TOTAL_EXPLICITO

F_TARIFA = Decimal("0.0005")        # 0.05 % — tarifa unitaria de Edificaciones
# OJO: los modelos `IGV` / `UIT` se importan arriba; estas constantes de
# arithmetic NO pueden llamarse igual o ensombrecen el import (bug: `IGV.objects`
# resolvia al Decimal). Por eso se nombran con sufijo explicito.
IGV_PORCENTAJE = Decimal("0.18")   # 18 %
UIT_VALOR = Decimal("5150.00")     # UIT vigente
VALOR_DECLARADO = Decimal("1000000.00")
TOTAL_EXPLICITO = Decimal("1000.00")
HABILITADAS_CATALOGO = 3


# ── Fixtures ────────────────────────────────────────────────────────────────────

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
def derecho_po_con_minimo(db):
    """Derecho vigente con piso UIT = 5150 × 0.10 = 515.00 y sin tope."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_po_con_maximo(db):
    """Derecho vigente sin piso y con tope máximo de 100.00."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=Decimal("100.00"),
        porcentaje_minimo_uit=Decimal("0"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _participante(especialidad, porcentaje=F_TARIFA, tarifa_id="tarifa-po-edificaciones"):
    """Construye el DTO de un participante (especialidad habilitada + tarifa)."""
    return TarifaPorcentajeObraAplicada(
        tarifa_id=tarifa_id,
        porcentaje_liquidacion=porcentaje,
        especialidad_id=str(especialidad.id),
        especialidad_nombre=especialidad.nombre,
    )


def _derecho_ctx(derecho):
    """Traduce el `DerechoPorcentajeObra` de BD al tipo canónico del motor."""
    return DerechoPOCotizacion(
        derecho_minimo=derecho.derecho_minimo,
        derecho_maximo=derecho.derecho_maximo,
        porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
        derecho_aplicado_id=str(derecho.id),
    )


def _contexto(estrategia, participantes, derecho, **overrides):
    """Arma el contexto canónico del motor para la estrategia indicada."""
    datos = {
        "estrategia": estrategia,
        "participantes": list(participantes),
        "count_habilitadas": HABILITADAS_CATALOGO,
        "porcentaje_tarifa": F_TARIFA,
        "valor_declarado": VALOR_DECLARADO,
        "igv_porcentaje": IGV_PORCENTAJE,
        "uit_valor": UIT_VALOR,
        "derecho": _derecho_ctx(derecho),
    }
    if estrategia == TOTAL:
        datos["total_explicito"] = TOTAL_EXPLICITO
    datos.update(overrides)
    return CotizacionPOContexto(**datos)


ESCENARIOS = [
    pytest.param(1, id="n-igual-a-1"),
    pytest.param(2, id="n-igual-a-H-menos-1"),
    pytest.param(3, id="n-igual-a-H"),
]

ESTRATEGIAS = [
    pytest.param(NORMAL, id="normal-seleccionadas"),
    pytest.param(HABILITADAS, id="tarifa-habilitadas-participantes"),
    pytest.param(TOTAL, id="total-explicito"),
]


# ── Matriz 3x3: estrategias × escenarios de participación ───────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("estrategia", ESTRATEGIAS)
@pytest.mark.parametrize("n_participantes", ESCENARIOS)
def test_matriz_3x3_modos_conserva_invariantes(
    estrategia,
    n_participantes,
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    GIVEN: un contexto válido de cualquiera de las tres estrategias.
    WHEN:  el motor calcula la cotización.
    THEN:  se cumplen I-1 (conservación del subtotal), I-2 (porcentajes del modo 2),
           I-3 (porcentajes NULL del modo 3), I-4 (modo 1 sin acumulación),
           I-5 (sin acumulación de diferencia cero) y la no-negatividad.
    """
    service = LiquidacionPorcentajeObraCoreService()
    especialidades = [
        especialidad_estructuras,
        especialidad_arquitectura,
        especialidad_installaciones,
    ]
    participantes = [_participante(esp) for esp in especialidades[:n_participantes]]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(estrategia, participantes, derecho_po_sin_rangos)
    )

    suma_detalles = sum((d.subtotal for d in cotizacion.detalles), Decimal("0"))
    acumulacion = cotizacion.acumulacion

    # I-1: conservación exacta del subtotal del padre
    if acumulacion is not None:
        assert suma_detalles + acumulacion.subtotal_acumulado == cotizacion.total_subtotal
    else:
        assert suma_detalles == cotizacion.total_subtotal

    # Conteos y no-negatividad
    assert cotizacion.count_participantes == len(cotizacion.detalles)
    assert cotizacion.count_participantes == n_participantes
    assert cotizacion.total_subtotal >= 0
    assert all(d.subtotal >= 0 for d in cotizacion.detalles)
    if acumulacion is not None:
        assert acumulacion.subtotal_acumulado > 0

    if estrategia == NORMAL:
        # I-4: el modo 1 nunca acumula
        assert acumulacion is None
        assert cotizacion.porcentaje_liquidacion == F_TARIFA * n_participantes
    elif estrategia == HABILITADAS:
        # El padre cobra H habilitadas; la diferencia porcentual va a la acumulación
        assert cotizacion.porcentaje_liquidacion == F_TARIFA * HABILITADAS_CATALOGO
        if acumulacion is not None:
            # I-2: parent's % == Σ(details %) + accumulated %
            assert acumulacion.porcentaje_acumulado == F_TARIFA * (
                HABILITADAS_CATALOGO - n_participantes
            )
            assert (
                cotizacion.porcentaje_liquidacion
                == sum((d.porcentaje_aplicado for d in cotizacion.detalles), Decimal("0"))
                + acumulacion.porcentaje_acumulado
            )
        else:
            # I-5: sin acumulación ⇒ todos los habilitadas participan
            assert n_participantes == HABILITADAS_CATALOGO
    else:
        # I-3: modo 3 sin porcentajes (padre, detalle y acumulación)
        assert cotizacion.porcentaje_liquidacion is None
        assert all(d.porcentaje_aplicado is None for d in cotizacion.detalles)
        if acumulacion is not None:
            assert acumulacion.porcentaje_acumulado is None
        # El total ingresado es autoritativo
        assert cotizacion.total == cotizacion.total_explicito
        assert cotizacion.total_subtotal + cotizacion.igv_monto == cotizacion.total


# ── Aritmética por estrategia ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_normal_seleccionadas_padre_y_detalles_sin_acumulacion(
    derecho_po_sin_rangos, especialidad_estructuras, especialidad_arquitectura
):
    """
    GIVEN: dos seleccionadas (escenario de la spec: padre 0.10 %).
    WHEN:  se cotiza con NORMAL_SELECCIONADAS.
    THEN:  el padre vale 0.10 %, hay un detalle por seleccionada y NO hay acumulación.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(NORMAL, participantes, derecho_po_sin_rangos)
    )

    assert cotizacion.estrategia == NORMAL
    assert cotizacion.porcentaje_liquidacion == Decimal("0.0010")
    assert cotizacion.total_subtotal == Decimal("1000.00")
    assert len(cotizacion.detalles) == 2
    assert cotizacion.detalles[0].subtotal == Decimal("500.00")
    assert cotizacion.detalles[1].subtotal == Decimal("500.00")
    assert cotizacion.acumulacion is None
    assert cotizacion.igv_monto == Decimal("180.00")
    assert cotizacion.total == Decimal("1180.00")


@pytest.mark.django_db
def test_tarifa_habilitadas_participantes_cobra_H_y_acumula_la_diferencia(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: H=3 habilitadas y n=1 participante con f=0.05 % (escenario de la spec:
           padre 0.15 %, detalle 0.05 %, acumulación 0.10 % + diferencia monetaria).
    WHEN:  se cotiza con TARIFA_HABILITADAS_PARTICIPANTES.
    THEN:  el padre cobra H×f, el participante recibe la cuota subtotal_padre/H y la
           diferencia se proyecta como acumulación.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(HABILITADAS, participantes, derecho_po_sin_rangos)
    )

    assert cotizacion.porcentaje_liquidacion == Decimal("0.0015")
    assert cotizacion.total_subtotal == Decimal("1500.00")
    assert len(cotizacion.detalles) == 1
    assert cotizacion.detalles[0].porcentaje_aplicado == Decimal("0.0005")
    assert cotizacion.detalles[0].subtotal == Decimal("500.00")
    assert cotizacion.detalles[0].importe_parcial == Decimal("500.00")

    assert cotizacion.acumulacion is not None
    assert cotizacion.acumulacion.porcentaje_acumulado == Decimal("0.0010")
    assert cotizacion.acumulacion.subtotal_acumulado == Decimal("1000.00")

    assert cotizacion.igv_monto == Decimal("270.00")
    assert cotizacion.total == Decimal("1770.00")


@pytest.mark.django_db
def test_total_explicito_extrae_subtotal_igv_y_cuota(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: total=177 con IGV 18 %, H=3 y n=1 (escenario de la spec).
    WHEN:  se cotiza con TOTAL_EXPLICITO.
    THEN:  subtotal=150.00, IGV=27.00 (por resta), detalle=50.00, acumulación=100.00
           con porcentaje NULL y el total se conserva en 177.00.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(
            TOTAL,
            participantes,
            derecho_po_sin_rangos,
            total_explicito=Decimal("177.00"),
        )
    )

    assert cotizacion.total_subtotal == Decimal("150.00")
    assert cotizacion.igv_monto == Decimal("27.00")
    assert cotizacion.total == Decimal("177.00")
    assert cotizacion.total_subtotal + cotizacion.igv_monto == cotizacion.total

    assert len(cotizacion.detalles) == 1
    assert cotizacion.detalles[0].subtotal == Decimal("50.00")
    assert cotizacion.detalles[0].porcentaje_aplicado is None

    assert cotizacion.porcentaje_liquidacion is None
    assert cotizacion.acumulacion is not None
    assert cotizacion.acumulacion.porcentaje_acumulado is None
    assert cotizacion.acumulacion.subtotal_acumulado == Decimal("100.00")


# ── Conservación de céntimos y determinismo ────────────────────────────────────

@pytest.mark.django_db
def test_reparto_conserva_centimos_y_es_determinista(
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    GIVEN: un total cuyo subtotal NO divide exacto entre H=3 (1000/1.18 = 847.46).
    WHEN:  se cotiza con TOTAL_EXPLICITO y n=2, en dos órdenes de entrada distintos.
    THEN:  la suma de los detalles es exactamente Q(subtotal × n/H), la acumulación
           conserva el resto, y el resultado NO depende del orden de llegada
           (orden canónico por especialidad_id ascendente).
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(TOTAL, participantes, derecho_po_sin_rangos)
    )

    subtotal = cotizacion.total_subtotal
    assert subtotal == Decimal("847.46")

    suma_detalles = sum((d.subtotal for d in cotizacion.detalles), Decimal("0"))
    assert suma_detalles == (subtotal * Decimal(2) / Decimal(3)).quantize(Decimal("0.01"))
    assert cotizacion.acumulacion.subtotal_acumulado == subtotal - suma_detalles
    assert suma_detalles + cotizacion.acumulacion.subtotal_acumulado == subtotal

    # Determinismo: el mismo conjunto en otro orden produce el mismo resultado
    invertida = service.calcular_cotizacion_po_estrategia(
        _contexto(TOTAL, list(reversed(participantes)), derecho_po_sin_rangos)
    )
    assert [d.subtotal for d in invertida.detalles] == [
        d.subtotal for d in cotizacion.detalles
    ]
    assert invertida.acumulacion.subtotal_acumulado == (
        cotizacion.acumulacion.subtotal_acumulado
    )


@pytest.mark.django_db
def test_total_explicito_con_H_completo_no_deja_acumulacion(
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    GIVEN: n == H (todos los habilitadas participan) con un subtotal no exacto.
    WHEN:  se cotiza con TOTAL_EXPLICITO.
    THEN:  no existe acumulación (invariante I-5) y el subtotal se conserva íntegro.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
        _participante(especialidad_installaciones),
    ]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(TOTAL, participantes, derecho_po_sin_rangos)
    )

    suma_detalles = sum((d.subtotal for d in cotizacion.detalles), Decimal("0"))
    assert suma_detalles == cotizacion.total_subtotal
    assert cotizacion.acumulacion is None


# ── Derechos ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_total_explicito_rechaza_subtotal_bajo_el_derecho_minimo(
    derecho_po_con_minimo, especialidad_estructuras
):
    """
    GIVEN: un total cuyo subtotal (150.00) queda bajo el piso UIT (515.00).
    WHEN:  se cotiza con TOTAL_EXPLICITO.
    THEN:  se RECHAZA con BusinessError; el total nunca se eleva en silencio.
    """
    service = LiquidacionPorcentajeObraCoreService()

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                TOTAL,
                [_participante(especialidad_estructuras)],
                derecho_po_con_minimo,
                total_explicito=Decimal("177.00"),
            )
        )

    assert exc_info.value.code == "PO_TOTAL_EXPLICITO_BAJO_DERECHO_MINIMO"
    assert exc_info.value.status_code == 400


@pytest.mark.django_db
def test_total_explicito_rechaza_subtotal_sobre_el_derecho_maximo(
    derecho_po_con_maximo, especialidad_estructuras
):
    """
    GIVEN: un total cuyo subtotal (150.00) excede el tope de derechos (100.00).
    WHEN:  se cotiza con TOTAL_EXPLICITO.
    THEN:  se RECHAZA con BusinessError; el total nunca se recorta en silencio.
    """
    service = LiquidacionPorcentajeObraCoreService()

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                TOTAL,
                [_participante(especialidad_estructuras)],
                derecho_po_con_maximo,
                total_explicito=Decimal("177.00"),
            )
        )

    assert exc_info.value.code == "PO_TOTAL_EXPLICITO_EXCEDE_DERECHO_MAXIMO"
    assert exc_info.value.status_code == 400


@pytest.mark.django_db
def test_motor_exige_habilitadas_resueltas_en_los_modos_con_universo(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: un contexto sin H resuelto (count_habilitadas=None).
    WHEN:  se cotiza con TARIFA_HABILITADAS_PARTICIPANTES.
    THEN:  se RECHAZA: el motor nunca deduce H a partir de los participantes.
    """
    service = LiquidacionPorcentajeObraCoreService()

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                HABILITADAS,
                [_participante(especialidad_estructuras)],
                derecho_po_sin_rangos,
                count_habilitadas=None,
            )
        )

    assert exc_info.value.code == "PO_HABILITADAS_NO_RESUELTAS"


@pytest.mark.django_db
def test_motor_rechaza_participantes_sobre_las_habilitadas(
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
):
    """
    GIVEN: 2 participantes con H=1 habilitada.
    WHEN:  se cotiza con TARIFA_HABILITADAS_PARTICIPANTES.
    THEN:  se RECHAZA con BusinessError.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                HABILITADAS,
                participantes,
                derecho_po_sin_rangos,
                count_habilitadas=1,
            )
        )

    assert exc_info.value.code == "PO_PARTICIPANTES_EXCEDEN_HABILITADAS"


@pytest.mark.django_db
def test_motor_rechaza_estrategia_no_soportada(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: una estrategia fuera del enum canónico (p. ej. una tarifa de subtotal fijo).
    WHEN:  se invoca el motor.
    THEN:  se RECHAZA con BusinessError y código propio.
    """
    service = LiquidacionPorcentajeObraCoreService()

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                "TARIFA_SUBTOTAL_FIJO",
                [_participante(especialidad_estructuras)],
                derecho_po_sin_rangos,
            )
        )

    assert exc_info.value.code == "PO_ESTRATEGIA_NO_SOPORTADA"


# ── Verificación de invariantes ────────────────────────────────────────────────

@pytest.mark.django_db
def test_verificar_invariantes_detecta_subtotal_inconsistente():
    """
    GIVEN: una proyección con un subtotal que no cierra con sus detalles.
    WHEN:  se verifica el invariante I-1.
    THEN:  se lanza BusinessError antes de cualquier commit.
    """
    service = LiquidacionPorcentajeObraCoreService()
    cotizacion = CotizacionPOEstrategiaData(
        estrategia=NORMAL,
        count_habilitadas=1,
        count_participantes=0,
        detalles=[],
        total_subtotal=Decimal("100.00"),
        total=Decimal("118.00"),
    )

    with pytest.raises(BusinessError) as exc_info:
        service.verificar_invariantes_po(cotizacion)

    assert exc_info.value.code == "PO_INVARIANTE_SUBTOTAL"


@pytest.mark.django_db
def test_verificar_invariantes_rechaza_acumulacion_en_modo_normal():
    """
    GIVEN: una proyección de NORMAL_SELECCIONADAS que trae acumulación.
    WHEN:  se verifica el invariante I-4.
    THEN:  se lanza BusinessError.
    """
    service = LiquidacionPorcentajeObraCoreService()
    cotizacion = CotizacionPOEstrategiaData(
        estrategia=NORMAL,
        count_habilitadas=1,
        count_participantes=0,
        detalles=[],
        total_subtotal=Decimal("10.00"),
        total=Decimal("11.80"),
        acumulacion={
            "porcentaje_acumulado": Decimal("0.0010"),
            "subtotal_acumulado": Decimal("10.00"),
        },
    )

    with pytest.raises(BusinessError) as exc_info:
        service.verificar_invariantes_po(cotizacion)

    assert exc_info.value.code == "PO_INVARIANTE_SIN_ACUMULACION"


# ── Proyección efímera ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_motor_no_persiste_padre_detalles_ni_acumulacion(
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    GIVEN: los tres modos calculados sobre el motor.
    WHEN:  se revisa la base de datos.
    THEN:  no existe ninguna fila de PO, de detalle ni de acumulación: en este módulo
           la acumulación es sólo una proyección efímera.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    for estrategia in (NORMAL, HABILITADAS, TOTAL):
        service.calcular_cotizacion_po_estrategia(
            _contexto(estrategia, participantes, derecho_po_sin_rangos)
        )

    assert LiquidacionPorcentajeObra.objects.count() == 0
    assert LiquidacionPorcentajeObraDetalle.objects.count() == 0
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


# ── Tasas históricas ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_motor_consume_las_tasas_historicas_resueltas_por_fecha_efectiva(
    igv_vigente,
    uit_vigente,
    derecho_po_sin_rangos,
    especialidad_estructuras,
):
    """
    GIVEN: IGV/UIT/derecho históricos (2020) y sus vigentes actuales en BD.
    WHEN:  se resuelven por la fecha efectiva 2020-06-15 y se cotiza con esos valores.
    THEN:  el motor usa las tasas HISTÓRICAS resueltas (IGV 10 %, UIT 3600) y no las
           vigentes del día; el contrato histórico queda preservado para edición.
    """
    service = LiquidacionPorcentajeObraCoreService()
    historico = LiquidacionPatchHistoricoCoreService()

    igv_historico = IGV.objects.create(
        valor=Decimal("0.10"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )
    uit_historico = UIT.objects.create(
        valor=Decimal("3600.00"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )
    derecho_historico = DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2020, 12, 31),
    )

    fecha_efectiva = date(2020, 6, 15)
    igv_resuelto = historico.get_igv_por_fecha(fecha_efectiva)
    uit_resuelto = historico.get_uit_por_fecha(fecha_efectiva)
    derecho_resuelto = historico.get_derecho_porcentaje_vigente(fecha_efectiva)

    assert igv_resuelto.id == igv_historico.id
    assert uit_resuelto.id == uit_historico.id
    assert derecho_resuelto.id == derecho_historico.id

    cotizacion = service.calcular_cotizacion_po_estrategia(
        CotizacionPOContexto(
            estrategia=HABILITADAS,
            participantes=[_participante(especialidad_estructuras)],
            count_habilitadas=HABILITADAS_CATALOGO,
            porcentaje_tarifa=F_TARIFA,
            valor_declarado=VALOR_DECLARADO,
            igv_porcentaje=igv_resuelto.valor,
            uit_valor=uit_resuelto.valor,
            derecho=DerechoPOCotizacion(
                derecho_minimo=derecho_resuelto.derecho_minimo,
                derecho_maximo=derecho_resuelto.derecho_maximo,
                porcentaje_minimo_uit=derecho_resuelto.porcentaje_minimo_uit,
                derecho_aplicado_id=str(derecho_resuelto.id),
            ),
        )
    )

    # padre = 1 000 000 × 0.0015 = 1500.00 ; IGV histórico 10 % ⇒ 150.00
    assert cotizacion.total_subtotal == Decimal("1500.00")
    assert cotizacion.igv_monto == Decimal("150.00")
    assert cotizacion.total == Decimal("1650.00")

    # Con las tasas de HOY el total sería 1770.00: el motor no las usa.
    assert cotizacion.total != Decimal("1770.00")
    assert historico.get_igv_por_fecha(date.today()).valor == Decimal("0.18")


# ── Fachada de compatibilidad ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_fachada_calcular_cotizacion_po_conserva_la_compatibilidad(
    derecho_po_sin_rangos, especialidad_estructuras, especialidad_arquitectura
):
    """
    GIVEN: la fachada pública usada por Taludes, Impacto Vial e import legacy.
    WHEN:  se invoca con los mismos argumentos que antes del motor por estrategia.
    THEN:  devuelve exactamente las mismas cifras que el motor en modo 1.
    """
    service = LiquidacionPorcentajeObraCoreService()
    tarifas = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    fachada = service.calcular_cotizacion_po(
        valor_declarado=VALOR_DECLARADO,
        tarifas=tarifas,
        igv_porcentaje=IGV_PORCENTAJE,
        derecho=derecho_po_sin_rangos,
        uit_valor=UIT_VALOR,
    )
    motor = service.calcular_cotizacion_po_estrategia(
        _contexto(NORMAL, tarifas, derecho_po_sin_rangos)
    )

    assert fachada.total_subtotal == motor.total_subtotal
    assert fachada.total == motor.total
    assert fachada.porcentaje_liquidacion == motor.porcentaje_liquidacion
    assert fachada.derecho_minimo == motor.derecho_minimo
    assert fachada.derecho_maximo == motor.derecho_maximo
    assert fachada.porcentaje_minimo_uit == motor.porcentaje_minimo_uit
    assert [d.subtotal for d in fachada.detalles] == [
        d.subtotal for d in motor.detalles
    ]
    assert [d.importe_parcial for d in fachada.detalles] == [
        d.importe_parcial for d in motor.detalles
    ]
    assert [d.ajuste_redondeo for d in fachada.detalles] == [
        d.ajuste_redondeo for d in motor.detalles
    ]


@pytest.mark.django_db
def test_fachada_calcular_cotizacion_po_respeta_el_bypass_legacy(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: el import legacy, que entrega subtotal y total ya calculados.
    WHEN:  se invoca la fachada con override_subtotal y override_total.
    THEN:  ambos valores se respetan tal cual (sin recalcular IGV).
    """
    service = LiquidacionPorcentajeObraCoreService()

    resultado = service.calcular_cotizacion_po(
        valor_declarado=VALOR_DECLARADO,
        tarifas=[_participante(especialidad_estructuras)],
        igv_porcentaje=IGV_PORCENTAJE,
        derecho=derecho_po_sin_rangos,
        uit_valor=UIT_VALOR,
        override_subtotal=Decimal("100.00"),
        override_total=Decimal("118.00"),
    )

    assert resultado.total_subtotal == Decimal("100.00")
    assert resultado.total == Decimal("118.00")
