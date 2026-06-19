"""
Unit tests for Finanzas HTTP schemas.
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.finanzas.presentation.schemas.finanzas_schemas import VariablesFinancierasOut


class TestVariablesFinancierasOut:
    """Test VariablesFinancierasOut schema."""

    def test_valid_output(self):
        """Output válido con todos los campos."""
        schema = VariablesFinancierasOut(
            igv_valor=0.18,
            igv_periodo_inicio="2020-01-01",
            uit_valor=4950.0,
            uit_periodo_inicio="2026-01-01",
        )
        assert schema.igv_valor == 0.18
        assert schema.igv_periodo_inicio == "2020-01-01"
        assert schema.uit_valor == 4950.0
        assert schema.uit_periodo_inicio == "2026-01-01"

    def test_igv_zero_valido(self):
        """igv_valor=0 es válido (no hay IGV)."""
        schema = VariablesFinancierasOut(
            igv_valor=0.0,
            igv_periodo_inicio="",
            uit_valor=0.0,
            uit_periodo_inicio="",
        )
        assert schema.igv_valor == 0.0

    def test_igv_high_value_valido(self):
        """igv_valor puede ser hasta 1.0 (100%)."""
        schema = VariablesFinancierasOut(
            igv_valor=1.0,
            igv_periodo_inicio="2000-01-01",
            uit_valor=3800.0,
            uit_periodo_inicio="2000-01-01",
        )
        assert schema.igv_valor == 1.0
