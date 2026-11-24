"""
Tests focalizados de la estrategia `TOTAL_EXPLICITO_SELECCIONADAS` (Edificaciones).

Cubre el contrato de la cuarta estrategia de cotización PO:

- el importe (total y subtotal) es AUTORITATIVO: no se recalcula desde el valor
  declarado ni desde la tarifa;
- el subtotal se reparte EXCLUSIVAMENTE entre las especialidades SELECCIONADAS
  (nunca entre H habilitadas);
- H (habilitadas) NUNCA se exige, se resuelve ni se persiste: queda NULL;
- los porcentajes del detalle y el porcentaje de tarifa son REFERENCIA;
- el padre no tiene porcentaje y nunca hay acumulación;
- la semántica de `TOTAL_EXPLICITO` NO cambia.

Tests DB-backed (pytest-django + ORM real, fixtures existentes). Sin mocks.
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command

from core.exceptions import BusinessError
from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
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
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    CotizacionPOContexto,
    DerechoPOCotizacion,
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_po_estrategia,
)


TOTAL_SELECCIONADAS = EstrategiaCotizacionPO.TOTAL_EXPLICITO_SELECCIONADAS

F_TARIFA = Decimal("0.0005")
IGV_PORCENTAJE = Decimal("0.18")
UIT_VALOR = Decimal("5150.00")
VALOR_DECLARADO = Decimal("1000000.00")
TOTAL_EXPLICITO = Decimal("1180.00")
SUBTOTAL_EXPLICITO = Decimal("1000.00")


# ── Fixtures ────────────────────────────────────────────────────────────────

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


# ── Helpers ─────────────────────────────────────────────────────────────────

def _participante(especialidad, porcentaje=F_TARIFA, tarifa_id="tarifa-po-edificaciones"):
    return TarifaPorcentajeObraAplicada(
        tarifa_id=tarifa_id,
        porcentaje_liquidacion=porcentaje,
        especialidad_id=str(especialidad.id),
        especialidad_nombre=especialidad.nombre,
    )


def _contexto(participantes, derecho, **overrides):
    """Contexto canónico del motor para TOTAL_EXPLICITO_SELECCIONADAS.

    NUNCA incluye `cantidad_especialidades_habilitadas`: la estrategia no usa H.
    """
    datos = {
        "estrategia": TOTAL_SELECCIONADAS,
        "participantes": list(participantes),
        "porcentaje_tarifa": F_TARIFA,
        "valor_declarado": VALOR_DECLARADO,
        "total_explicito": TOTAL_EXPLICITO,
        "igv_porcentaje": IGV_PORCENTAJE,
        "uit_valor": UIT_VALOR,
        "derecho": DerechoPOCotizacion(
            derecho_minimo=derecho.derecho_minimo,
            derecho_maximo=derecho.derecho_maximo,
            porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
            derecho_aplicado_id=str(derecho.id),
        ),
    }
    datos.update(overrides)
    return CotizacionPOContexto(**datos)


# ── Motor ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_motor_no_exige_h_y_persiste_h_nulo(
    derecho_po_sin_rangos, especialidad_estructuras, especialidad_arquitectura
):
    """
    GIVEN: un contexto SIN `cantidad_especialidades_habilitadas` (H).
    WHEN:  el motor cotiza con TOTAL_EXPLICITO_SELECCIONADAS.
    THEN:  no se exige H (no hay PO_HABILITADAS_NO_RESUELTAS) y la proyección
           devuelve H = NULL.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
    ]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(participantes, derecho_po_sin_rangos)
    )

    assert cotizacion.cantidad_especialidades_habilitadas is None
    assert cotizacion.count_participantes == 2


@pytest.mark.django_db
def test_motor_preserva_el_importe_entrante_sin_recalcularlo(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: un total y un subtotal explícitos (históricos).
    WHEN:  el motor cotiza.
    THEN:  el total y el subtotal se conservan EXACTOS: no se recalculan desde
           el valor declarado ni desde la tarifa, y el IGV es la resta.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(
            participantes,
            derecho_po_sin_rangos,
            total_explicito=TOTAL_EXPLICITO,
            subtotal_explicito=SUBTOTAL_EXPLICITO,
        )
    )

    assert cotizacion.total == TOTAL_EXPLICITO
    assert cotizacion.total_subtotal == SUBTOTAL_EXPLICITO
    assert cotizacion.igv_monto == TOTAL_EXPLICITO - SUBTOTAL_EXPLICITO
    # El valor declarado NO participa en el cálculo del importe.
    assert cotizacion.total_subtotal != VALOR_DECLARADO * F_TARIFA


@pytest.mark.django_db
def test_motor_deriva_el_subtotal_del_total_cuando_no_viene(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: sólo el total explícito.
    WHEN:  el motor cotiza.
    THEN:  el subtotal se deriva del total por IGV (mismo criterio que
           TOTAL_EXPLICITO) y subtotal + igv == total exacto.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(participantes, derecho_po_sin_rangos)
    )

    esperado = (TOTAL_EXPLICITO / (Decimal("1") + IGV_PORCENTAJE)).quantize(
        Decimal("0.01")
    )
    assert cotizacion.total_subtotal == esperado
    assert cotizacion.total_subtotal + cotizacion.igv_monto == cotizacion.total


@pytest.mark.django_db
def test_motor_reparte_el_subtotal_solo_entre_las_seleccionadas(
    derecho_po_sin_rangos,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
):
    """
    GIVEN: 3 seleccionadas con H = 4 habilitadas implícito en el contexto.
    WHEN:  el motor cotiza.
    THEN:  el subtotal se reparte entre las 3 SELECCIONADAS (no entre H) y la
           suma de los detalles es EXACTA (invariante I-1 sin acumulación).
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [
        _participante(especialidad_estructuras),
        _participante(especialidad_arquitectura),
        _participante(especialidad_installaciones),
    ]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(
            participantes,
            derecho_po_sin_rangos,
            subtotal_explicito=SUBTOTAL_EXPLICITO,
            cantidad_especialidades_habilitadas=4,
        )
    )

    suma = sum((d.subtotal for d in cotizacion.detalles), Decimal("0"))
    assert suma == cotizacion.total_subtotal == SUBTOTAL_EXPLICITO
    assert len(cotizacion.detalles) == 3
    # El reparto NO es `subtotal / H`: es `subtotal / n`.
    assert cotizacion.detalles[0].subtotal == (
        SUBTOTAL_EXPLICITO / Decimal("3")
    ).quantize(Decimal("0.01"))


@pytest.mark.django_db
def test_motor_no_genera_acumulacion_y_el_padre_no_tiene_porcentaje(
    derecho_po_sin_rangos, especialidad_estructuras
):
    """
    GIVEN: una cotización con TOTAL_EXPLICITO_SELECCIONADAS.
    WHEN:  se inspecciona la proyección.
    THEN:  no hay acumulación, el padre no tiene porcentaje y los porcentajes
           del detalle se conservan como REFERENCIA.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(participantes, derecho_po_sin_rangos)
    )

    assert cotizacion.acumulacion is None
    assert cotizacion.porcentaje_liquidacion is None
    assert cotizacion.porcentaje_tarifa == F_TARIFA
    assert cotizacion.detalles[0].porcentaje_aplicado == F_TARIFA
    assert cotizacion.detalles[0].tarifa_aplicada is not None


@pytest.mark.django_db
def test_motor_rechaza_sin_participantes(derecho_po_sin_rangos):
    """
    GIVEN: un contexto sin seleccionadas.
    WHEN:  el motor cotiza.
    THEN:  se rechaza con PO_SIN_PARTICIPANTES.
    """
    service = LiquidacionPorcentajeObraCoreService()

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto([], derecho_po_sin_rangos)
        )

    assert exc_info.value.code == "PO_SIN_PARTICIPANTES"


@pytest.mark.django_db
def test_motor_rechaza_total_invalido(derecho_po_sin_rangos, especialidad_estructuras):
    """
    GIVEN: un total explícito no positivo.
    WHEN:  el motor cotiza.
    THEN:  se rechaza con PO_TOTAL_EXPLICITO_INVALIDO.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(participantes, derecho_po_sin_rangos, total_explicito=Decimal("0"))
        )

    assert exc_info.value.code == "PO_TOTAL_EXPLICITO_INVALIDO"


@pytest.mark.django_db
def test_motor_rechaza_subtotal_fuera_de_rango_sin_elevarlo(
    db, especialidad_estructuras
):
    """
    GIVEN: un subtotal explícito por debajo del derecho mínimo.
    WHEN:  el motor cotiza.
    THEN:  se RECHAZA (nunca se eleva ni se ajusta el importe histórico).
    """
    derecho = DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            _contexto(
                participantes,
                derecho,
                subtotal_explicito=Decimal("10.00"),
            )
        )

    assert exc_info.value.code == "PO_TOTAL_EXPLICITO_BAJO_DERECHO_MINIMO"


@pytest.mark.django_db
def test_motor_conserva_los_montos_historicos_legacy_sin_revalidarlos(
    db, especialidad_estructuras
):
    """
    GIVEN: un subtotal histórico (override) por debajo del derecho mínimo.
    WHEN:  el motor cotiza.
    THEN:  los montos históricos son autoritativos: se conservan y NO se
           re-validan (nunca se elevan).
    """
    derecho = DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    cotizacion = service.calcular_cotizacion_po_estrategia(
        _contexto(
            participantes,
            derecho,
            subtotal_explicito=None,
            override_subtotal=Decimal("10.00"),
            override_total=Decimal("11.80"),
        )
    )

    assert cotizacion.total_subtotal == Decimal("10.00")
    assert cotizacion.total == Decimal("11.80")


@pytest.mark.django_db
def test_total_explicito_conserva_su_semantica(derecho_po_sin_rangos, especialidad_estructuras):
    """
    GIVEN: la estrategia TOTAL_EXPLICITO (la preexistente).
    WHEN:  el motor cotiza.
    THEN:  sigue exigiendo H y repartiendo `subtotal / H` con acumulación: la
           semántica existente NO cambia.
    """
    service = LiquidacionPorcentajeObraCoreService()
    participantes = [_participante(especialidad_estructuras)]

    with pytest.raises(BusinessError) as exc_info:
        service.calcular_cotizacion_po_estrategia(
            CotizacionPOContexto(
                estrategia=EstrategiaCotizacionPO.TOTAL_EXPLICITO,
                participantes=participantes,
                valor_declarado=VALOR_DECLARADO,
                total_explicito=TOTAL_EXPLICITO,
                igv_porcentaje=IGV_PORCENTAJE,
                uit_valor=UIT_VALOR,
                derecho=DerechoPOCotizacion(porcentaje_minimo_uit=Decimal("0")),
            )
        )

    assert exc_info.value.code == "PO_HABILITADAS_NO_RESUELTAS"


# ── Contrato API ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_api_acepta_el_discriminador_nuevo(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload con la estrategia TOTAL_EXPLICITO_SELECCIONADAS.
    WHEN:  se crea la liquidación.
    THEN:  200; la estrategia persistida es la nueva y H queda NULL.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
    )

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    tipo = response.json()["data"]["liquidacion_tipo"]
    assert tipo["estrategia_cotizacion"] == TOTAL_SELECCIONADAS
    assert tipo["cantidad_especialidades_habilitadas"] is None
    assert tipo["acumulacion"] is None
    assert tipo["porcentaje_liquidacion"] is None


@pytest.mark.django_db
def test_api_rechaza_campos_de_otra_estrategia(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload de TOTAL_EXPLICITO_SELECCIONADAS con `subtotal_explicito`
           en el nivel equivocado (dato de otra estrategia).
    WHEN:  se crea la liquidación.
    THEN:  422 (union discriminada estricta).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
        datos_extra={"total_explicito": None},
    )

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_api_rechaza_enviar_h(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload que intenta enviar H (habilitadas).
    WHEN:  se crea la liquidación.
    THEN:  422 — el cliente NUNCA envía H en esta estrategia.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
    )
    payload["liquidacion_especifica"]["cantidad_especialidades_habilitadas"] = 4

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 422, f"{response.status_code}: {response.content}"


@pytest.mark.django_db
def test_api_preserva_el_subtotal_explicito_enviado(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: un payload con total y subtotal explícitos.
    WHEN:  se crea la liquidación.
    THEN:  los importes se conservan: el total del padre y el subtotal del
           padre son los enviados (no se recalculan).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
        datos_extra={"subtotal_explicito": float(SUBTOTAL_EXPLICITO)},
    )

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    data = response.json()["data"]
    general = data["liquidacion_general"]
    assert Decimal(str(general["total"])) == TOTAL_EXPLICITO
    assert Decimal(str(general["sub_total"])) == SUBTOTAL_EXPLICITO


# ── Edición: el importe histórico se preserva y H sigue NULL ─────────────────

@pytest.mark.django_db
def test_patch_preserva_el_importe_historico_y_deja_h_nulo(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una liquidación creada con TOTAL_EXPLICITO_SELECCIONADAS.
    WHEN:  se re-cotiza con la MISMA estrategia (modo preservar).
    THEN:  los importes NO se recalculan (se preservan los históricos), H
           sigue NULL y no aparece ninguna fila de acumulación.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
    )
    create = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert create.status_code == 200, f"{create.status_code}: {create.content}"
    liquidacion_id = create.json()["data"]["liquidacion_general"]["id"]
    general_inicial = create.json()["data"]["liquidacion_general"]

    patch_payload = {
        "liquidacion_tipo": {
            "estrategia_cotizacion": TOTAL_SELECCIONADAS,
            "datos": {"valor_declarado": float(VALOR_DECLARADO)},
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                    "especialidad_id": str(especialidad_estructuras.id),
                }
            ],
        }
    }
    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=patch_payload,
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    tipo = response.json()["data"]["liquidacion_tipo"]
    assert tipo["estrategia_cotizacion"] == TOTAL_SELECCIONADAS
    assert tipo["cantidad_especialidades_habilitadas"] is None
    assert tipo["acumulacion"] is None

    general = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(general["total"])) == Decimal(str(general_inicial["total"]))
    assert Decimal(str(general["sub_total"])) == Decimal(
        str(general_inicial["sub_total"])
    )

    po = LiquidacionPorcentajeObra.objects.get(liquidacion_general_id=liquidacion_id)
    assert po.cantidad_especialidades_habilitadas is None
    assert not LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=po
    ).exists()


@pytest.mark.django_db
def test_cotizar_edicion_no_exige_h_ni_recalcula_el_importe(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una liquidación creada con TOTAL_EXPLICITO_SELECCIONADAS.
    WHEN:  se pide el preview de `cotizar-edicion`.
    THEN:  200 sin exigir H y con los MISMOS importes de la liquidación.
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL_SELECCIONADAS,
        total_explicito=float(TOTAL_EXPLICITO),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
    )
    create = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert create.status_code == 200, f"{create.status_code}: {create.content}"
    liquidacion_id = create.json()["data"]["liquidacion_general"]["id"]
    general_inicial = create.json()["data"]["liquidacion_general"]

    edicion_payload = {
        "liquidacion_tipo": {
            "estrategia_cotizacion": TOTAL_SELECCIONADAS,
            "datos": {
                "valor_declarado": float(VALOR_DECLARADO),
                "total_explicito": float(TOTAL_EXPLICITO),
            },
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                    "especialidad_id": str(especialidad_estructuras.id),
                }
            ],
        }
    }
    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=edicion_payload,
    )
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    data = response.json()["data"]
    assert data["estrategia_cotizacion"] == TOTAL_SELECCIONADAS
    assert data["cantidad_especialidades_habilitadas"] is None
    assert data["acumulacion"] is None
    assert Decimal(str(data["total"])) == Decimal(str(general_inicial["total"]))
    assert Decimal(str(data["total_subtotal"])) == Decimal(
        str(general_inicial["sub_total"])
    )


# ── Comando de corrección ───────────────────────────────────────────────────

def _crear_modificacion_legacy(
    municipalidad,
    proyecto,
    create_user,
    tipo_edificacion,
    especialidad_estructuras,
    tarifa_porcentaje_obra_estructuras,
    sub_total,
    total,
    estrategia="TOTAL_EXPLICITO",
    h=3,
):
    """Crea una liquidación legacy de 'modificación de licencia' con 1 detalle."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    liquidacion = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        legacy=True,
        sub_total=sub_total,
        total=total,
        tipo_liquidacion=tipo_edificacion,
        estado="PENDIENTE",
        numero_revision=1,
        denominacion_de_proyecto="MODIFICACION DE LICENCIA",
    )
    edificacion = LiquidacionEdificacion.objects.create(liquidacion=liquidacion, numero=1)
    porcentaje = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion,
        estrategia_cotizacion=estrategia,
        cantidad_especialidades_habilitadas=h,
        porcentaje_liquidacion=None,
        porcentaje_tarifa=Decimal("0.0005"),
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
    )
    detalle = LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=porcentaje,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad_id=especialidad_estructuras.id,
        subtotal=(sub_total / Decimal(h)).quantize(Decimal("0.01")),
        importe_parcial=(sub_total / Decimal(h)).quantize(Decimal("0.01")),
        ajuste_redondeo=Decimal("0.00"),
        porcentaje_aplicado=None,
    )
    return liquidacion, porcentaje, detalle


@pytest.mark.django_db
def test_comando_correccion_dry_run_no_escribe(
    tmp_path, municipalidad, proyecto, create_user, tipo_edificacion,
    especialidad_estructuras, tarifa_porcentaje_obra_estructuras,
):
    """
    GIVEN: una modificación legacy repartida por H=3.
    WHEN:  se ejecuta el comando SIN `--apply`.
    THEN:  no escribe nada (la estrategia sigue siendo la anterior) y deja el
           CSV de auditoría.
    """
    liquidacion, porcentaje, detalle = _crear_modificacion_legacy(
        municipalidad,
        proyecto,
        create_user,
        tipo_edificacion,
        especialidad_estructuras,
        tarifa_porcentaje_obra_estructuras,
        Decimal("1000.00"),
        Decimal("1180.00"),
    )
    csv_path = tmp_path / "auditoria.csv"

    call_command("correct_legacy_edif_modificacion_po", csv_output=str(csv_path))

    porcentaje.refresh_from_db()
    detalle.refresh_from_db()
    assert porcentaje.estrategia_cotizacion == "TOTAL_EXPLICITO"
    assert porcentaje.cantidad_especialidades_habilitadas == 3
    assert detalle.subtotal != liquidacion.sub_total

    assert csv_path.exists()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["status"] == "PLANNED"
    assert rows[0]["estrategia_propuesta"] == TOTAL_SELECCIONADAS


@pytest.mark.django_db
def test_comando_correccion_apply_regulariza_y_conserva_los_importes_del_padre(
    tmp_path, municipalidad, proyecto, create_user, tipo_edificacion,
    especialidad_estructuras, tarifa_porcentaje_obra_estructuras,
):
    """
    GIVEN: una modificación legacy repartida por H=3.
    WHEN:  se ejecuta el comando con `--apply`.
    THEN:  la estrategia pasa a TOTAL_EXPLICITO_SELECCIONADAS, H queda NULL, el
           detalle conserva el importe histórico completo y los importes
           AUTORITATIVOS del padre (`sub_total` y `total`) NO se tocan.
    """
    liquidacion, porcentaje, detalle = _crear_modificacion_legacy(
        municipalidad,
        proyecto,
        create_user,
        tipo_edificacion,
        especialidad_estructuras,
        tarifa_porcentaje_obra_estructuras,
        Decimal("1000.00"),
        Decimal("1180.00"),
    )
    subtotal_original = liquidacion.sub_total
    total_original = liquidacion.total
    csv_path = tmp_path / "auditoria.csv"

    call_command(
        "correct_legacy_edif_modificacion_po",
        apply=True,
        csv_output=str(csv_path),
    )

    porcentaje.refresh_from_db()
    detalle.refresh_from_db()
    liquidacion.refresh_from_db()

    assert porcentaje.estrategia_cotizacion == TOTAL_SELECCIONADAS
    assert porcentaje.cantidad_especialidades_habilitadas is None
    assert porcentaje.porcentaje_liquidacion is None
    assert porcentaje.total_explicito == total_original
    assert detalle.subtotal == subtotal_original
    assert detalle.importe_parcial == subtotal_original

    # Los importes autoritativos del padre NO se tocan.
    assert liquidacion.sub_total == subtotal_original
    assert liquidacion.total == total_original

    # No queda fila de acumulación.
    assert not LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=porcentaje
    ).exists()


@pytest.mark.django_db
def test_comando_correccion_es_idempotente(
    tmp_path, municipalidad, proyecto, create_user, tipo_edificacion,
    especialidad_estructuras, tarifa_porcentaje_obra_estructuras,
):
    """
    GIVEN: una modificación legacy repartida por H=3.
    WHEN:  se ejecuta el comando con `--apply` dos veces.
    THEN:  la segunda ejecución no vuelve a tocar el registro (idempotencia).
    """
    liquidacion, porcentaje, detalle = _crear_modificacion_legacy(
        municipalidad,
        proyecto,
        create_user,
        tipo_edificacion,
        especialidad_estructuras,
        tarifa_porcentaje_obra_estructuras,
        Decimal("1000.00"),
        Decimal("1180.00"),
    )
    csv_path = tmp_path / "auditoria.csv"

    call_command(
        "correct_legacy_edif_modificacion_po",
        apply=True,
        csv_output=str(csv_path),
    )
    call_command(
        "correct_legacy_edif_modificacion_po",
        apply=True,
        csv_output=str(csv_path),
    )

    porcentaje.refresh_from_db()
    detalle.refresh_from_db()
    assert porcentaje.estrategia_cotizacion == TOTAL_SELECCIONADAS
    assert porcentaje.cantidad_especialidades_habilitadas is None
    assert detalle.subtotal == liquidacion.sub_total


# ── Clasificación RH ────────────────────────────────────────────────────────

def test_clasificacion_rh_tiene_rama_propia_para_la_estrategia_nueva():
    """
    GIVEN: un PO con TOTAL_EXPLICITO_SELECCIONADAS.
    WHEN:  se clasifica su reparto.
    THEN:  usa la rama propia (no la de TOTAL_EXPLICITO ni la genérica).
    """
    from types import SimpleNamespace

    from modules.liquidaciones.management.commands.reconcile_legacy_edif_rh import (
        po_allocation_classification,
    )
    from modules.liquidaciones.management.commands.restore_legacy_edif_rh_h3 import (
        po_category,
    )

    porcentaje = SimpleNamespace(
        estrategia_cotizacion="TOTAL_EXPLICITO_SELECCIONADAS",
        porcentaje_tarifa=Decimal("0.0005"),
        cantidad_especialidades_habilidades=None,
        cantidad_especialidades_habilitadas=None,
    )

    assert (
        po_allocation_classification(porcentaje, 1)
        == "PO_TOTAL_EXPLICITO_SELECCIONADAS_POR_DETALLE"
    )
    assert po_category(porcentaje) == "TOTAL_EXPLICITO_SELECCIONADAS"
