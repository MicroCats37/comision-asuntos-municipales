"""
Unit tests for calculation helpers (_calcular_monto_m2 and _calcular_monto_visitas).

Tests:
- M2: area_m2 floor, clamps (min/max), decimal precision
- Visitas: visitas_minimas floor, decimal multiplication
- Edge cases: zero values, exact boundary values

NOTE: These are PURE functions with no ORM/DB dependencies.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.services.core.calculos_helpers import (
    _calcular_monto_m2,
    _calcular_monto_visitas,
    _aplicar_derecho_minimo,
    _aplicar_derecho_maximo,
)


class TestCalcularMontoM2:
    """Test _calcular_monto_m2 with various scenarios."""

    def test_area_solicitada_mayor_a_minima_usa_area_solicitada(self):
        """
        Si area_solicitada > area_m2, debe usar area_solicitada para cálculo.
        """
        area_solicitada = Decimal("150.00")  # 150 m2
        costo_m2 = Decimal("50.0000")  # S/ 50/m2
        area_m2 = Decimal("100.00")  # 100 m2 mínimo
        derecho_minimo = Decimal("500.00")
        derecho_maximo = Decimal("5000.00")

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # area_calculo = max(150, 100) = 150
        assert area_calculo == Decimal("150.00")
        # derecho = 150 * 50 = 7500, pero está capped at derecho_maximo = 5000
        assert derecho == Decimal("5000.00")

    def test_area_solicitada_menor_a_minima_usa_area_m2(self):
        """
        Si area_solicitada < area_m2, debe usar area_m2 para cálculo.
        Escenario del spec: área 50m2 con mínimo 100m2 → usar 100m2.
        """
        area_solicitada = Decimal("50.00")  # 50 m2 (menor al mínimo)
        costo_m2 = Decimal("50.0000")  # S/ 50/m2
        area_m2 = Decimal("100.00")  # 100 m2 mínimo
        derecho_minimo = Decimal("500.00")
        derecho_maximo = None  # Sin tope

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # area_calculo = max(50, 100) = 100
        assert area_calculo == Decimal("100.00")
        # derecho = 100 * 50 = 5000 (sin tope, está sobre mínimo)
        assert derecho == Decimal("5000.00")

    def test_area_solicitada_igual_a_minima_usa_area_m2(self):
        """
        Si area_solicitada == area_m2, debe usar ese valor.
        """
        area_solicitada = Decimal("100.00")
        costo_m2 = Decimal("50.0000")
        area_m2 = Decimal("100.00")
        derecho_minimo = Decimal("500.00")
        derecho_maximo = None

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        assert area_calculo == Decimal("100.00")
        assert derecho == Decimal("5000.00")

    def test_derecho_aplicado_cuando_monto_base_menor_a_minimo(self):
        """
        Si monto_base < derecho_minimo, debe retornar derecho_minimo.
        Escenario: área 5m2 × S/ 10/m2 = S/ 50 < derecho_minimo S/ 500 → usar S/ 500.
        """
        area_solicitada = Decimal("5.00")
        costo_m2 = Decimal("10.0000")
        area_m2 = Decimal("100.00")  # Se usa 100 no 5
        derecho_minimo = Decimal("500.00")
        derecho_maximo = None

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # area_calculo = max(5, 100) = 100
        assert area_calculo == Decimal("100.00")
        # monto_base = 100 * 10 = 1000, pero > derecho_minimo (500), no se aplica floor
        assert derecho == Decimal("1000.00")

    def test_derecho_minimo_absoluto_cuando_monto_base_muy_pequeno(self):
        """
        Escenario real: área 1m2 × S/ 10/m2 = S/ 10 < derecho_minimo S/ 500 → S/ 500.
        """
        area_solicitada = Decimal("1.00")
        costo_m2 = Decimal("10.0000")
        area_m2 = Decimal("100.00")  # Se usa 100
        derecho_minimo = Decimal("500.00")
        derecho_maximo = None

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # monto_base = 100 * 10 = 1000 > 500, no se aplica mínimo
        assert derecho == Decimal("1000.00")

    def test_derecho_maximo_capped_cuando_monto_excede(self):
        """
        Si monto_base > derecho_maximo, debe retornar derecho_maximo.
        Escenario: 150m2 × S/ 50/m2 = S/ 7500 > derecho_maximo S/ 5000 → S/ 5000.
        """
        area_solicitada = Decimal("150.00")
        costo_m2 = Decimal("50.0000")
        area_m2 = Decimal("100.00")
        derecho_minimo = Decimal("500.00")
        derecho_maximo = Decimal("5000.00")

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        assert area_calculo == Decimal("150.00")
        # 150 * 50 = 7500, pero capped at 5000
        assert derecho == Decimal("5000.00")

    def test_derecho_entre_minimo_y_maximo_retorna_monto_base(self):
        """
        Si derecho está entre mínimo y máximo, retorna monto_base sin modificar.
        Escenario: 80m2 × S/ 50/m2 = S/ 4000, entre 500 y 5000 → S/ 4000.
        """
        area_solicitada = Decimal("80.00")
        costo_m2 = Decimal("50.0000")
        area_m2 = Decimal("100.00")  # Usa 100
        derecho_minimo = Decimal("500.00")
        derecho_maximo = Decimal("5000.00")

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # monto = 100 * 50 = 5000, que es exactamente el máximo
        assert area_calculo == Decimal("100.00")
        assert derecho == Decimal("5000.00")

    def test_sin_derecho_maximo_sin_tope(self):
        """
        Si derecho_maximo=None, no hay techo.
        Escenario: 200m2 × S/ 50/m2 = S/ 10000, sin máximo → S/ 10000.
        """
        area_solicitada = Decimal("200.00")
        costo_m2 = Decimal("50.0000")
        area_m2 = Decimal("100.00")
        derecho_minimo = Decimal("500.00")
        derecho_maximo = None

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        assert area_calculo == Decimal("200.00")
        assert derecho == Decimal("10000.00")

    def test_decimal_precision_4_decimal_places(self):
        """
        Verifica que el cálculo mantiene precisión de 4 decimales.
        Escenario: 123.4567m2 × S/ 12.3456/m2.
        """
        area_solicitada = Decimal("123.4567")
        costo_m2 = Decimal("12.3456")
        area_m2 = Decimal("50.00")
        derecho_minimo = Decimal("100.00")
        derecho_maximo = None

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        assert area_calculo == Decimal("123.4567")
        # 123.4567 * 12.3456 = 1524.14703552 (full precision, no rounding in helper)
        assert derecho == Decimal("1524.14703552")

    def test_cero_area_solicitada_con_minimo_positivo(self):
        """
        Escenario edge: area_solicitada=0, area_m2=100 → usa 100.
        """
        area_solicitada = Decimal("0.00")
        costo_m2 = Decimal("50.0000")
        area_m2 = Decimal("100.00")
        derecho_minimo = Decimal("500.00")
        derecho_maximo = Decimal("5000.00")

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # max(0, 100) = 100
        assert area_calculo == Decimal("100.00")
        # 100 * 50 = 5000, capped at 5000
        assert derecho == Decimal("5000.00")

    def test_minimo_y_maximo_iguales_aplica_solo_un_valor(self):
        """
        Si derecho_minimo == derecho_maximo, el resultado siempre es ese valor
        cuando el monto calculado es distinto.
        """
        area_solicitada = Decimal("10.00")
        costo_m2 = Decimal("10.0000")
        area_m2 = Decimal("10.00")
        derecho_minimo = Decimal("1000.00")
        derecho_maximo = Decimal("1000.00")

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada,
            costo_m2=costo_m2,
            area_m2=area_m2,
            derecho_minimo=derecho_minimo,
            derecho_maximo=derecho_maximo,
        )

        # monto = 10 * 10 = 100, menor a mínimo 1000 → se eleva a 1000
        assert area_calculo == Decimal("10.00")
        assert derecho == Decimal("1000.00")


class TestCalcularMontoVisitas:
    """Test _calcular_monto_visitas with various scenarios."""

    def test_visitas_solicitadas_mayores_a_minimas_usa_solicitadas(self):
        """
        Si cantidad_visitas > visitas_minimas, debe usar cantidad_visitas.
        """
        cantidad_visitas = 5
        costo_visita = Decimal("150.00")
        visitas_minimas = 1

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 5
        assert derecho == Decimal("750.00")  # 5 × 150

    def test_visitas_solicitadas_menores_a_minimas_usa_minimas(self):
        """
        Si cantidad_visitas < visitas_minimas, debe usar visitas_minimas.
        Escenario del spec: 0 visitas con mínimo 1 → usar 1.
        """
        cantidad_visitas = 0
        costo_visita = Decimal("150.00")
        visitas_minimas = 1

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 1  # max(0, 1) = 1
        assert derecho == Decimal("150.00")

    def test_visitas_solicitadas_iguales_a_minimas(self):
        """
        Si cantidad_visitas == visitas_minimas, usa ese valor.
        """
        cantidad_visitas = 3
        costo_visita = Decimal("100.00")
        visitas_minimas = 3

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 3
        assert derecho == Decimal("300.00")

    def test_cero_visitas_con_minimo(self):
        """
        Escenario edge: 0 visitas con mínimo 2 → usa 2.
        """
        cantidad_visitas = 0
        costo_visita = Decimal("200.00")
        visitas_minimas = 2

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 2
        assert derecho == Decimal("400.00")

    def test_visitas_grande_calculo_correcto(self):
        """
        Escenario: 10 visitas × S/ 150/visita = S/ 1500.
        """
        cantidad_visitas = 10
        costo_visita = Decimal("150.00")
        visitas_minimas = 1

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 10
        assert derecho == Decimal("1500.00")

    def test_decimal_precision_en_costo_visita(self):
        """
        Verifica precisión decimal en costo por visita.
        Escenario: 3 visitas × S/ 123.45/visita.
        """
        cantidad_visitas = 3
        costo_visita = Decimal("123.45")
        visitas_minimas = 1

        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=costo_visita,
            visitas_minimas=visitas_minimas,
        )

        assert visitas_calculo == 3
        assert derecho == Decimal("370.35")


class TestAplicarDerechoMinimo:
    """Test _aplicar_derecho_minimo helper."""

    def test_monto_menor_a_minimo_retorna_minimo(self):
        """Si monto < derecho_minimo, retorna derecho_minimo."""
        resultado = _aplicar_derecho_minimo(
            monto=Decimal("100.00"),
            derecho_minimo=Decimal("500.00"),
        )
        assert resultado == Decimal("500.00")

    def test_monto_igual_a_minimo_retorna_monto(self):
        """Si monto == derecho_minimo, retorna el monto."""
        resultado = _aplicar_derecho_minimo(
            monto=Decimal("500.00"),
            derecho_minimo=Decimal("500.00"),
        )
        assert resultado == Decimal("500.00")

    def test_monto_mayor_a_minimo_retorna_monto(self):
        """Si monto > derecho_minimo, retorna el monto original."""
        resultado = _aplicar_derecho_minimo(
            monto=Decimal("1000.00"),
            derecho_minimo=Decimal("500.00"),
        )
        assert resultado == Decimal("1000.00")


class TestAplicarDerechoMaximo:
    """Test _aplicar_derecho_maximo helper."""

    def test_monto_mayor_a_maximo_retorna_maximo(self):
        """Si monto > derecho_maximo, retorna derecho_maximo."""
        resultado = _aplicar_derecho_maximo(
            monto=Decimal("8000.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("5000.00")

    def test_monto_igual_a_maximo_retorna_monto(self):
        """Si monto == derecho_maximo, retorna el monto."""
        resultado = _aplicar_derecho_maximo(
            monto=Decimal("5000.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("5000.00")

    def test_monto_menor_a_maximo_retorna_monto(self):
        """Si monto < derecho_maximo, retorna el monto original."""
        resultado = _aplicar_derecho_maximo(
            monto=Decimal("3000.00"),
            derecho_maximo=Decimal("5000.00"),
        )
        assert resultado == Decimal("3000.00")

    def test_derecho_maximo_none_sin_tope(self):
        """Si derecho_maximo=None, retorna el monto sin modificar."""
        resultado = _aplicar_derecho_maximo(
            monto=Decimal("100000.00"),
            derecho_maximo=None,
        )
        assert resultado == Decimal("100000.00")
