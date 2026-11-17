"""
Tests del MOTOR ÚNICO de cotización de Visitas (Inspección de Obra) por MODO.

Cubre el bloque A de la exploración `io-continuity-server-quote`:
- A-2: `calcular_cotizacion_visitas_puro` extrae la aritmética y la fachada
  `calcular_cotizacion_visitas` conserva las MISMAS cifras.
- A-4: `calcular_credito_continuidad` (bruto → neto → bruto, cuantizado).
- A-5: `calcular_cotizacion_visitas_estrategia` despacha NORMAL | CONTINUAR.
- A-6: `verificar_invariantes_visitas` (IV-1..IV-8) antes de devolver.
- A-7: `construir_contexto_visitas` es la factory única del contexto.

Base de la aritmética (fixtures compartidas de `tests/fixtures/`):
- UIT vigente 5150.00 · IGV vigente 0.18 · porcentaje_uit 0.05
- 3 visitas → 3 × (0.05 × 5150.00) = 772.50 neto · 772.50 × 1.18 = 911.55 bruto

Los tests del motor son PUROS (sin base de datos): el contexto llega resuelto.
"""
from decimal import Decimal

import pytest

from core.exceptions import BusinessError
from modules.liquidaciones.domain.constants import ModoCotizacionVisitas
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)

# ── Base aritmética de los tests ──────────────────────────────────────────────

UIT_VALOR = Decimal("5150.00")
IGV = Decimal("0.18")
PORCENTAJE_UIT = Decimal("0.05")
CANTIDAD_VISITAS = 3

# 3 × (0.05 × 5150.00) = 772.50
NETO_ESPERADO = Decimal("772.50")
# 772.50 × 1.18 = 911.55
BRUTO_ESPERADO = Decimal("911.55")


def _contexto_normal(**kwargs):
    """Contexto NORMAL resuelto (3 visitas, tarifa 5 % UIT, IGV 0.18)."""
    base = dict(
        modo=ModoCotizacionVisitas.NORMAL,
        cantidad_visitas=CANTIDAD_VISITAS,
        porcentaje_uit=PORCENTAJE_UIT,
        uit_valor=UIT_VALOR,
        igv_porcentaje=IGV,
        categoria="INSPECCION",
        tarifa_id="tarifa-1",
        uit_id="uit-1",
        igv_id="igv-1",
    )
    base.update(kwargs)
    return LiquidacionPorCategoriaVisitasCoreService.construir_contexto_visitas(**base)


# ── NORMAL: byte-compatibilidad con la aritmética vigente ─────────────────────


def test_motor_normal_reproduce_la_aritmetica_vigente():
    """
    GIVEN: contexto NORMAL resuelto (3 visitas, 5 % UIT, IGV 0.18).
    WHEN:  el motor calcula la cotización.
    THEN:  subtotal 772.50 y total 911.55 (idéntico a la aritmética vigente).
    """
    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        _contexto_normal()
    )

    assert cotizacion.modo == ModoCotizacionVisitas.NORMAL
    assert cotizacion.costo_por_visita == Decimal("257.50")
    assert cotizacion.subtotal == NETO_ESPERADO
    assert cotizacion.monto_bruto == NETO_ESPERADO
    assert cotizacion.total == BRUTO_ESPERADO


def test_motor_normal_no_cuantiza_el_total():
    """
    IV-7: en NORMAL el total NO se cuantiza (compatibilidad byte a byte).

    El total conserva la precisión completa de la aritmética vigente: si se
    cuantizara, el `total` del preview dejaría de coincidir con el histórico.
    """
    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        _contexto_normal()
    )

    assert cotizacion.total.as_tuple().exponent < -2, (
        "El total de NORMAL debe conservar la aritmética sin cuantizar "
        f"(exponente {cotizacion.total.as_tuple().exponent})."
    )


def test_motor_normal_no_devuelve_bloque_de_continuidad():
    """NORMAL no lleva bloque `continuidad`: la respuesta lo devuelve en null."""
    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        _contexto_normal()
    )

    assert cotizacion.continuidad is None


@pytest.mark.django_db
def test_motor_normal_coincide_con_la_fachada_de_compatibilidad(
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    A-2: la fachada `calcular_cotizacion_visitas` (compatibilidad) y el motor
    NORMAL producen EXACTAMENTE las mismas cifras.
    """
    core = LiquidacionPorCategoriaVisitasCoreService()

    fachada = core.calcular_cotizacion_visitas(
        cantidad_visitas=CANTIDAD_VISITAS,
        tarifa_visitas_id=str(tarifa_visitas_io.id),
        uit_vigente=uit_vigente,
        igv_vigente=igv_vigente,
    )
    motor = core.calcular_cotizacion_visitas_estrategia(
        _contexto_normal(
            porcentaje_uit=Decimal(str(tarifa_visitas_io.porcentaje_uit)),
            uit_valor=Decimal(str(uit_vigente.valor)),
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            categoria=tarifa_visitas_io.categoria_visitas,
            tarifa_id=str(tarifa_visitas_io.id),
            uit_id=str(uit_vigente.id),
            igv_id=str(igv_vigente.id),
        )
    )

    assert fachada is not None
    assert fachada.subtotal == motor.subtotal
    assert fachada.total == motor.total
    assert fachada.monto_bruto == motor.monto_bruto
    assert fachada.costo_por_visita == motor.costo_por_visita
    assert fachada.categoria == motor.categoria


# ── CONTINUAR: aritmética cuantizada y crédito derivado ───────────────────────


def test_motor_continuar_devuelve_las_cifras_autoritativas():
    """
    AS-2: en CONTINUAR el motor devuelve valor completo, crédito y diferencia,
    netos y brutos, TODO cuantizado a 2 decimales.
    """
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        total_pagado_previa=Decimal("212.40"),
    )

    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        contexto
    )
    continuidad = cotizacion.continuidad

    assert continuidad is not None
    assert continuidad.total_pagado_previa == Decimal("212.40")
    assert continuidad.valor_completo_neto == NETO_ESPERADO
    assert continuidad.valor_completo_bruto == BRUTO_ESPERADO
    # 212.40 ÷ 1.18 = 180.00 → 180.00 × 1.18 = 212.40
    assert continuidad.credito_neto == Decimal("180.00")
    assert continuidad.credito_bruto == Decimal("212.40")
    # 772.50 − 180.00 = 592.50 · 911.55 − 212.40 = 699.15
    assert continuidad.diferencia_neto == Decimal("592.50")
    assert continuidad.diferencia_bruto == Decimal("699.15")
    assert continuidad.igv_porcentaje == IGV

    # El bloque `calculo` lleva el VALOR COMPLETO de B.
    assert cotizacion.monto_bruto == NETO_ESPERADO
    assert cotizacion.subtotal == NETO_ESPERADO
    assert cotizacion.total == BRUTO_ESPERADO


def test_motor_continuar_cuantiza_todas_las_cifras():
    """En CONTINUAR todas las cifras se cuantizan a 2 decimales (ROUND_HALF_UP)."""
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        total_pagado_previa=Decimal("212.40"),
    )

    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        contexto
    )
    continuidad = cotizacion.continuidad

    for valor in (
        cotizacion.total,
        cotizacion.subtotal,
        continuidad.valor_completo_neto,
        continuidad.valor_completo_bruto,
        continuidad.credito_neto,
        continuidad.credito_bruto,
        continuidad.diferencia_neto,
        continuidad.diferencia_bruto,
    ):
        assert valor.as_tuple().exponent == -2, f"{valor} no está cuantizado a 2 decimales."


def test_motor_continuar_deriva_el_credito_desde_el_bruto_declarado():
    """
    A-4: el servidor es la autoridad de la conversión del bruto declarado.

    212.60 ÷ 1.18 = 180.1694… → 180.17 (cuantizado) · 180.17 × 1.18 = 212.60

    La conversión NO es idempotente al céntimo (riesgo R1 del diseño): por eso
    el motor devuelve SIEMPRE las cifras derivadas y el bruto declarado solo
    se devuelve como eco.
    """
    credito_neto, credito_bruto = LiquidacionPorCategoriaVisitasCoreService.calcular_credito_continuidad(
        Decimal("212.60"), IGV
    )

    assert credito_neto == Decimal("180.17")
    assert credito_bruto == Decimal("212.60")


def test_motor_continuar_redondea_el_credito_de_un_bruto_exacto():
    """Un bruto declarado exacto (212.40) se convierte sin pérdida: 180.00 / 212.40."""
    credito_neto, credito_bruto = LiquidacionPorCategoriaVisitasCoreService.calcular_credito_continuidad(
        Decimal("212.40"), IGV
    )

    assert credito_neto == Decimal("180.00")
    assert credito_bruto == Decimal("212.40")


def test_motor_continuar_usa_el_credito_neto_resuelto_cuando_no_hay_bruto():
    """
    Regla de precedencia del motor (2): si no hay bruto declarado, se usa el
    neto ya resuelto y el bruto se deriva con el IGV de la ruta.
    """
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        credito_neto=Decimal("180.00"),
    )

    cotizacion = LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(
        contexto
    )

    assert cotizacion.continuidad.credito_neto == Decimal("180.00")
    assert cotizacion.continuidad.credito_bruto == Decimal("212.40")


# ── Invariantes (IV-1..IV-8): se verifican ANTES de devolver ─────────────────


def test_invariante_iv5_rechaza_credito_mayor_al_valor_completo():
    """
    IV-5: el crédito NO puede superar el valor completo del trabajo → 400.
    """
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        total_pagado_previa=Decimal("1000.00"),
    )

    with pytest.raises(BusinessError) as exc:
        LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(contexto)

    assert exc.value.status_code == 400
    assert exc.value.code == "IO_INVARIANTE_CREDITO_MAYOR_VALOR_COMPLETO"


def test_invariante_iv8_rechaza_bruto_declarado_no_positivo():
    """IV-8: el bruto declarado es > 0 (y <= 9999999999.99)."""
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        total_pagado_previa=Decimal("0"),
    )

    with pytest.raises(BusinessError) as exc:
        LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(contexto)

    assert exc.value.status_code == 400
    assert exc.value.code == "IO_INVARIANTE_TOTAL_PAGADO_PREVIA"


def test_invariante_iv8_rechaza_bruto_declarado_fuera_de_rango():
    """IV-8: el bruto declarado no puede superar 9999999999.99."""
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        total_pagado_previa=Decimal("10000000000.00"),
    )

    with pytest.raises(BusinessError) as exc:
        LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(contexto)

    assert exc.value.status_code == 400
    assert exc.value.code == "IO_INVARIANTE_TOTAL_PAGADO_PREVIA"


def test_invariante_iv3_rechaza_credito_negativo():
    """IV-3: el crédito no puede ser negativo."""
    contexto = _contexto_normal(
        modo=ModoCotizacionVisitas.CONTINUAR,
        credito_neto=Decimal("-10.00"),
    )

    with pytest.raises(BusinessError) as exc:
        LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(contexto)

    assert exc.value.status_code == 400
    assert exc.value.code == "IO_INVARIANTE_CREDITO_NO_NEGATIVO"


def test_motor_rechaza_modo_no_soportado():
    """El motor solo conoce NORMAL y CONTINUAR: cualquier otro modo es un 400."""
    contexto = _contexto_normal(modo="OTRO")

    with pytest.raises(BusinessError) as exc:
        LiquidacionPorCategoriaVisitasCoreService().calcular_cotizacion_visitas_estrategia(contexto)

    assert exc.value.status_code == 400
    assert exc.value.code == "IO_MODO_COTIZACION_NO_SOPORTADO"
