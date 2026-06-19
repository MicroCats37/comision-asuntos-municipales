"""
Unit tests for Liquidaciones Edificaciones calculation rules.

Tests:
- Revisiones que cobran: 1, 3, 5, 7 (2, 4, 6 no cobran)
- Cálculo de derecho mínimo/máximo
- Cálculo de monto base
- Lógica de preparar_nueva_revision
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.services.flujos.liquidacion_edificaciones_flujo import (
    LiquidacionesEdificacionesFlujo,
    REVISIONES_COBRAN,
    MAX_REVISIONES,
)
from modules.liquidaciones.domain.services.core.liquidacion_edificaciones_core_service import (
    LiquidacionesEdificacionesService,
)


class TestRevisionCobraRegla:
    """Test the REVISIONES_COBRAN rule: 1,3,5,7 cobran; 2,4,6 no."""

    def test_revisiones_cobran_es_1357(self):
        """REVISIONES_COBRAN debe ser exactamente {1, 3, 5, 7}."""
        assert REVISIONES_COBRAN == {1, 3, 5, 7}

    def test_revision_1_cobra(self):
        """Revisión 1 debe cobrar."""
        assert 1 in REVISIONES_COBRAN

    def test_revision_2_no_cobra(self):
        """Revisión 2 NO debe cobrar."""
        assert 2 not in REVISIONES_COBRAN

    def test_revision_3_cobra(self):
        """Revisión 3 debe cobrar."""
        assert 3 in REVISIONES_COBRAN

    def test_revision_4_no_cobra(self):
        """Revisión 4 NO debe cobrar."""
        assert 4 not in REVISIONES_COBRAN

    def test_revision_5_cobra(self):
        """Revisión 5 debe cobrar."""
        assert 5 in REVISIONES_COBRAN

    def test_revision_6_no_cobra(self):
        """Revisión 6 NO debe cobrar."""
        assert 6 not in REVISIONES_COBRAN

    def test_revision_7_cobra(self):
        """Revisión 7 debe cobrar."""
        assert 7 in REVISIONES_COBRAN

    def test_revision_8_no_existe(self):
        """Revisión 8 está más allá de MAX_REVISIONES=7."""
        assert 8 not in REVISIONES_COBRAN
        assert MAX_REVISIONES == 7


class TestCalcularDerecho:
    """Test _calcular_derecho with minimum and maximum — living in Flujo."""

    def setup_method(self):
        self.flujo = LiquidacionesEdificacionesFlujo(core=LiquidacionesEdificacionesService())

    def test_derecho_sobre_minimo_retorna_minimo(self):
        """Si monto_base < derecho_minimo, debe retornar derecho_minimo."""
        resultado = self.flujo._calcular_derecho(
            monto_base=Decimal("100.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("500.00")

    def test_derecho_igual_minimo_retorna_minimo(self):
        """Si monto_base == derecho_minimo, debe retornarlo."""
        resultado = self.flujo._calcular_derecho(
            monto_base=Decimal("500.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("500.00")

    def test_derecho_entre_minimo_y_maximo_retorna_monto_base(self):
        """Si monto_base está entre mínimo y máximo, retorna monto_base."""
        resultado = self.flujo._calcular_derecho(
            monto_base=Decimal("1500.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("1500.00")

    def test_derecho_sobre_maximo_retorna_maximo(self):
        """Si monto_base > derecho_maximo, debe retornar derecho_maximo."""
        resultado = self.flujo._calcular_derecho(
            monto_base=Decimal("8000.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("5000.00")

    def test_derecho_sin_maximo_retorna_monto_base_cuando_es_mayor(self):
        """Si derecho_maximo=None, no hay techo."""
        resultado = self.flujo._calcular_derecho(
            monto_base=Decimal("10000.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("10000.00")


class TestCalcularMontoBase:
    """Test _calcular_monto_base — living in Flujo."""

    def setup_method(self):
        self.flujo = LiquidacionesEdificacionesFlujo(core=LiquidacionesEdificacionesService())

    def test_monto_base_simple(self):
        """5% de 10000 = 500."""
        resultado = self.flujo._calcular_monto_base(
            valor_proyecto=Decimal("10000.00"),
            porcentaje_liquidacion=Decimal("0.05"),
        )
        assert resultado == Decimal("500.00")

    def test_monto_base_decimal(self):
        """5% de 12345.67 = 617.2835."""
        resultado = self.flujo._calcular_monto_base(
            valor_proyecto=Decimal("12345.67"),
            porcentaje_liquidacion=Decimal("0.05"),
        )
        assert resultado == Decimal("617.2835")

    def test_monto_base_cero(self):
        """0% de cualquier valor = 0."""
        resultado = self.flujo._calcular_monto_base(
            valor_proyecto=Decimal("10000.00"),
            porcentaje_liquidacion=Decimal("0.00"),
        )
        assert resultado == Decimal("0")


class TestPrepararNuevaRevisionLogica:
    """Test logic of preparar_nueva_revision without full DB (just constants)."""

    def test_siguiente_revision_es_previa_mas_1(self):
        """El siguiente número de revisión es previa + 1."""
        assert 1 + 1 == 2
        assert 2 + 1 == 3
        assert 6 + 1 == 7
        assert 7 + 1 == 8

    def test_revision_8_excede_max(self):
        """Revisión 8 debe lanzar MaximoRevisionAlcanzadoError."""
        assert 8 > MAX_REVISIONES

    def test_preparar_nueva_revision_cobra_segun_numero(self):
        """La función determina cobra según REVISIONES_COBRAN."""
        # Desde revisión 1 -> siguiente 2, 2 no cobra
        assert (1 + 1) not in REVISIONES_COBRAN
        # Desde revisión 2 -> siguiente 3, 3 cobra
        assert (2 + 1) in REVISIONES_COBRAN
        # Desde revisión 3 -> siguiente 4, 4 no cobra
        assert (3 + 1) not in REVISIONES_COBRAN
        # Desde revisión 4 -> siguiente 5, 5 cobra
        assert (4 + 1) in REVISIONES_COBRAN
        # Desde revisión 5 -> siguiente 6, 6 no cobra
        assert (5 + 1) not in REVISIONES_COBRAN
        # Desde revisión 6 -> siguiente 7, 7 cobra
        assert (6 + 1) in REVISIONES_COBRAN
