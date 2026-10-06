"""
Tarifas M2 (Por Metro Cuadrado) fixtures — HU and MS tariff setup.

Re-exports: tarifa_liquidacion_base_hu, tarifa_m2_hu,
            tarifa_liquidacion_base_ms, tarifa_m2_ms,
            derecho_m2_vigente
"""
import pytest
from decimal import Decimal
from datetime import date
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)


# ── Habilitación Urbana ──────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_hu(db, tipo_habilitacion_urbana):
    """Create a TarifaLiquidacionBase for Habilitacion Urbana."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tarifa_liquidacion_base_hu):
    """Create a TarifaPorMetroCuadrado for Habilitacion Urbana."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_hu,
        costo_por_m2=Decimal("150.0000"),
    )


# ── Mecánica de Suelos ───────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_ms(db, tipo_mecanica_suelos):
    """Create a TarifaLiquidacionBase for Mecánica de Suelos."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_liquidacion_base_ms):
    """Create a TarifaPorMetroCuadrado for Mecánica de Suelos."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_ms,
        costo_por_m2=Decimal("150.0000"),
    )


# ── Shared Derecho M2 ─────────────────────────────────────────────────────────

@pytest.fixture
def derecho_m2_vigente(db):
    """Create a DerechoPorMetroCuadrado vigente for testing (shared by HU and MS)."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
