"""
Tests for liquidacion_porcentaje_obra_core_service — calcular_cotizacion_po.

Covers the Shadow Mode high-precision fields:
- importe_parcial: theoretical value per specialty, quantized to 2dp
- ajuste_redondeo: 0.00 for all details except the last, which receives the remainder
- subtotal: the authoritative per-specialty amount (previously called importe_total)

Tests use the service directly (no Django ORM) for pure-unit verification.
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP

from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    TarifaPorcentajeObraAplicada,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tarifa(tarifa_id: str, porcentaje: Decimal, especialidad_id: str = "esp-1") -> TarifaPorcentajeObraAplicada:
    """Build a TarifaPorcentajeObraAplicada DTO."""
    return TarifaPorcentajeObraAplicada(
        tarifa_id=tarifa_id,
        porcentaje_liquidacion=porcentaje,
        especialidad_id=especialidad_id,
        especialidad_nombre=f"Especialidad {especialidad_id}",
    )


def _mock_derecho(
    porcentaje_minimo_uit: Decimal = Decimal("0.10"),
    derecho_minimo: Decimal | None = None,
    derecho_maximo: Decimal | None = None,
) -> object:
    """Build a mock-like DerechoPorcentajeObra object (plain attribute holder)."""
    class MockDerecho:
        def __init__(self):
            self.porcentaje_minimo_uit = porcentaje_minimo_uit
            self.derecho_minimo = derecho_minimo
            self.derecho_maximo = derecho_maximo
            self.id = "derecho-uuid-001"
    return MockDerecho()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_calcular_cotizacion_po_odd_division_ajuste_redondeo_absorbs_delta():
    """
    PRORATE ODD-DIVISION: tarifas 0.33 + 0.34 + 0.34 = 1.01.

    valor_declarado=99999 → subtotal_bruto=100998.99 (overrides minimo=515).

    With Decimal arithmetic, 0.33/1.01, 0.34/1.01, 0.34/1.01 produce exact results
    when multiplied by 100998.99 — the remainder gets absorbed by the last detail.

    Invariants verified:
      1. SUM(subtotal) == total_subtotal exactly
      2. All Decimal fields have at most 2 decimal places
    """
    service = LiquidacionPorcentajeObraCoreService()

    tarifas = [
        _tarifa("t1", Decimal("0.33"), "esp-1"),
        _tarifa("t2", Decimal("0.34"), "esp-2"),
        _tarifa("t3", Decimal("0.34"), "esp-3"),
    ]

    result = service.calcular_cotizacion_po(
        valor_declarado=Decimal("99999.00"),
        tarifas=tarifas,
        igv_porcentaje=Decimal("0.18"),
        derecho=_mock_derecho(porcentaje_minimo_uit=Decimal("0.10")),
        uit_valor=Decimal("5150.00"),
    )

    # porcentaje_total = 0.33 + 0.34 + 0.34 = 1.01
    assert result.porcentaje_liquidacion == Decimal("1.01")

    # subtotal_bruto = 99999 × 1.01 = 100998.99; minimo = 515; subtotal_total = 100998.99
    assert result.total_subtotal == Decimal("100998.99")
    assert result.total_subtotal == sum(d.subtotal for d in result.detalles)

    assert len(result.detalles) == 3

    # Verify all 3 detail Decimal fields are populated and ≤ 2dp
    for i, d in enumerate(result.detalles):
        for field_name in ["importe_parcial", "ajuste_redondeo", "subtotal"]:
            val = getattr(d, field_name)
            assert val is not None, f"Detalle {i}.{field_name} must not be None"
            assert val.as_tuple().exponent >= -2, (
                f"Detalle {i}.{field_name}={val} exceeds 2 decimal places"
            )


def test_calcular_cotizacion_po_minimo_uit_applies_to_total_not_per_tarifa():
    """
    Verify that the derecho minimo applies to the TOTAL liquidacion, not per-tarifa.

    Scenario: valor_declarado=10000 (small), minimo=515 (uit×0.10).
    subtotal_bruto = 10000 × 0.001 (all tarifas) = 10.00 << minimo(515.00)
    → subtotal_total = 515.00 (clamped to minimo).

    This proves the minimo is applied once to the aggregate, not per specialty.
    """
    service = LiquidacionPorcentajeObraCoreService()

    tarifas = [
        _tarifa("t1", Decimal("0.0003"), "esp-1"),  # 0.03%
        _tarifa("t2", Decimal("0.0004"), "esp-2"),  # 0.04%
        _tarifa("t3", Decimal("0.0003"), "esp-3"),  # 0.03%
        # total = 0.0010
    ]

    derecho = _mock_derecho(
        porcentaje_minimo_uit=Decimal("0.10"),  # minimo = 515.00
        derecho_minimo=Decimal("100.00"),        # unused — computed from uit
    )
    uit_valor = Decimal("5150.00")  # minimo = 5150 × 0.10 = 515.00

    result = service.calcular_cotizacion_po(
        valor_declarado=Decimal("10000.00"),
        tarifas=tarifas,
        igv_porcentaje=Decimal("0.18"),
        derecho=derecho,
        uit_valor=uit_valor,
    )

    # subtotal_bruto = 10000 × 0.001 = 10.00, but minimo = 515.00
    # → subtotal_total = 515.00 (derecho_minimo applied to total, not per tarifa)
    assert result.total_subtotal == Decimal("515.00")

    # The sum of subtotals must equal subtotal_total
    suma_subtotals = sum(d.subtotal for d in result.detalles)
    assert suma_subtotals == Decimal("515.00")


def test_calcular_cotizacion_po_single_tarifa_no_ajuste():
    """
    Single tariff: no rounding division needed. ajuste_redondeo must be 0.00
    and SUM(subtotal) must equal total_subtotal exactly.
    """
    service = LiquidacionPorcentajeObraCoreService()

    tarifas = [_tarifa("t1", Decimal("0.0010"), "esp-1")]

    result = service.calcular_cotizacion_po(
        valor_declarado=Decimal("100000.00"),
        tarifas=tarifas,
        igv_porcentaje=Decimal("0.18"),
        derecho=_mock_derecho(porcentaje_minimo_uit=Decimal("0.10")),
        uit_valor=Decimal("5150.00"),
    )

    assert len(result.detalles) == 1
    d = result.detalles[0]
    assert d.ajuste_redondeo == Decimal("0.00")
    assert d.subtotal == d.importe_parcial
    assert d.subtotal == result.total_subtotal


def test_calcular_cotizacion_po_equal_proportions_clean_split():
    """
    Two equal tariffs (0.50 + 0.50) with odd subtotal 99999.99.
    Each half: 99999.99 × 0.50 = 49999.995 → quantized 50000.00 (ROUND_HALF_UP).
    SUM of quantized partials = 100000.00, which is 0.01 MORE than subtotal_total.
    The LAST detail absorbs the overage: its subtotal = 49999.99 (-0.01).

    This proves the rounding correction works: SUM(subtotal) == subtotal_total exactly.
    """
    service = LiquidacionPorcentajeObraCoreService()

    tarifas = [
        _tarifa("t1", Decimal("0.50"), "esp-1"),
        _tarifa("t2", Decimal("0.50"), "esp-2"),
    ]

    result = service.calcular_cotizacion_po(
        valor_declarado=Decimal("99999.99"),
        tarifas=tarifas,
        igv_porcentaje=Decimal("0.18"),
        derecho=_mock_derecho(porcentaje_minimo_uit=Decimal("0.10")),
        uit_valor=Decimal("5150.00"),
    )

    assert result.total_subtotal == Decimal("99999.99")
    assert len(result.detalles) == 2

    # Detalle 1 (idx=0, NOT last): 49999.995 → quantized 50000.00; no adjustment
    assert result.detalles[0].importe_parcial == Decimal("50000.00"), (
        f"Detalle 0: expected 50000.00, got {result.detalles[0].importe_parcial}"
    )
    assert result.detalles[0].ajuste_redondeo == Decimal("0.00")
    assert result.detalles[0].subtotal == Decimal("50000.00")

    # Detalle 2 (idx=1, LAST): absorbs the overage.
    # ajuste_total = 99999.99 - (50000.00 + 50000.00) = -0.01
    # → ajuste_redondeo = -0.01, subtotal = 50000.00 - 0.01 = 49999.99
    assert result.detalles[1].ajuste_redondeo == Decimal("-0.01"), (
        f"Detalle 1 ajuste_redondeo: expected -0.01, got {result.detalles[1].ajuste_redondeo}"
    )
    assert result.detalles[1].subtotal == Decimal("49999.99"), (
        f"Detalle 1 subtotal: expected 49999.99, got {result.detalles[1].subtotal}"
    )
    assert result.detalles[1].importe_parcial == Decimal("50000.00")

    # CRITICAL INVARIANT: SUM(subtotal) == total_subtotal exactly
    suma = sum(d.subtotal for d in result.detalles)
    assert suma == Decimal("99999.99"), (
        f"SUM(subtotal)={suma} != total_subtotal=99999.99"
    )
