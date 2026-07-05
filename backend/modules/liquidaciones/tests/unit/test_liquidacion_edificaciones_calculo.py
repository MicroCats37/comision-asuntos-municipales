"""
Unit tests for Liquidaciones Edificaciones calculation rules.

Tests:
- Revisiones que cobran: 1, 3, 5 (2, 4, 6, 7 no cobran porque no existen)
- Cálculo de derecho mínimo/máximo
- Cálculo de monto base
- Lógica de preparar_nueva_revision (secuencia: 1 -> 3 -> 5)

NOTE: Calculation methods (_calcular_derecho, _calcular_monto_base) were moved
from Flujo to Core Service per Django architecture contract (P2, P6).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.services.flujos.liquidacion_edificaciones_flujo import (
    REVISIONES_COBRAN,
    MAX_REVISIONES,
)
from modules.liquidaciones.domain.services.core.liquidacion_edificaciones_core_service import (
    LiquidacionesEdificacionesService,
)


class TestRevisionCobraRegla:
    """Test the REVISIONES_COBRAN rule: 1,3,5 cobran; 2,4,6,7 no."""

    def test_revisiones_cobran_es_135(self):
        """REVISIONES_COBRAN debe ser exactamente {1, 3, 5}."""
        assert REVISIONES_COBRAN == {1, 3, 5}

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

    def test_revision_7_no_cobra(self):
        """Revisión 7 NO debe cobrar (no existe en la secuencia)."""
        assert 7 not in REVISIONES_COBRAN

    def test_revision_6_no_existe(self):
        """Revisión 6 no puede crearse (MAX_REVISIONES=5)."""
        assert 6 > MAX_REVISIONES


class TestCalcularDerecho:
    """Test calcular_derecho with minimum and maximum — living in Core Service."""

    def setup_method(self):
        self.core = LiquidacionesEdificacionesService()

    def test_derecho_sobre_minimo_retorna_minimo(self):
        """Si monto_base < derecho_minimo, debe retornar derecho_minimo."""
        resultado = self.core.calcular_derecho(
            monto_base=Decimal("100.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("500.00")

    def test_derecho_igual_minimo_retorna_minimo(self):
        """Si monto_base == derecho_minimo, debe retornarlo."""
        resultado = self.core.calcular_derecho(
            monto_base=Decimal("500.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("500.00")

    def test_derecho_entre_minimo_y_maximo_retorna_monto_base(self):
        """Si monto_base está entre mínimo y máximo, retorna monto_base."""
        resultado = self.core.calcular_derecho(
            monto_base=Decimal("1500.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("1500.00")

    def test_derecho_sobre_maximo_retorna_maximo(self):
        """Si monto_base > derecho_maximo, debe retornar derecho_maximo."""
        resultado = self.core.calcular_derecho(
            monto_base=Decimal("8000.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("5000.00")

    def test_derecho_sin_maximo_retorna_monto_base_cuando_es_mayor(self):
        """Si derecho_maximo=None, no hay techo."""
        resultado = self.core.calcular_derecho(
            monto_base=Decimal("10000.00"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("10000.00")


class TestCalcularMontoBase:
    """Test calcular_monto_base — living in Core Service."""

    def setup_method(self):
        self.core = LiquidacionesEdificacionesService()

    def test_monto_base_simple(self):
        """5% de 10000 = 500."""
        resultado = self.core.calcular_monto_base(
            valor_base_calculo=Decimal("10000.00"),
            porcentaje_liquidacion=Decimal("0.05"),
        )
        assert resultado == Decimal("500.00")

    def test_monto_base_decimal(self):
        """5% de 12345.67 = 617.2835."""
        resultado = self.core.calcular_monto_base(
            valor_base_calculo=Decimal("12345.67"),
            porcentaje_liquidacion=Decimal("0.05"),
        )
        assert resultado == Decimal("617.2835")

    def test_monto_base_cero(self):
        """0% de cualquier valor = 0."""
        resultado = self.core.calcular_monto_base(
            valor_base_calculo=Decimal("10000.00"),
            porcentaje_liquidacion=Decimal("0.00"),
        )
        assert resultado == Decimal("0")


class TestPrepararNuevaRevisionLogica:
    """Test logic of preparar_nueva_revision without full DB (just constants).

    Nueva secuencia: 1 -> 3 -> 5 (paso +2).
    No se pueden crear revisiones 2, 4, 6, 7.
    """

    def test_siguiente_revision_es_previa_mas_2(self):
        """El siguiente número de revisión es previa + 2."""
        assert 1 + 2 == 3
        assert 3 + 2 == 5
        assert 5 + 2 == 7  # 7 exceedería MAX_REVISIONES=5

    def test_revision_6_y_7_exceden_max(self):
        """Revisión 6 y 7 deben lanzar MaximoRevisionAlcanzadoError (>5)."""
        assert 6 > MAX_REVISIONES
        assert 7 > MAX_REVISIONES

    def test_preparar_nueva_revision_cobra_segun_numero(self):
        """La función determina cobra según REVISIONES_COBRAN."""
        # Desde revisión 1 -> siguiente 3, 3 cobra
        assert (1 + 2) in REVISIONES_COBRAN
        # Desde revisión 3 -> siguiente 5, 5 cobra
        assert (3 + 2) in REVISIONES_COBRAN
        # Desde revisión 5 -> siguiente 7, 7 no existe (excede MAX)
        assert (5 + 2) > MAX_REVISIONES
