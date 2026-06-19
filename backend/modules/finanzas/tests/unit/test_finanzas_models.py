"""
Unit tests for Finanzas models — tests IGV/UIT esta_vigente property.
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.finanzas.tests.factories.igv_factory import IGVFactory
from modules.finanzas.tests.factories.uit_factory import UITFactory


@pytest.mark.django_db
class TestIGVVigenteProperty:
    """Test IGV.vigente property."""

    def test_igv_sin_periodo_fin_es_vigente(self):
        """IGV sin periodo_fin debe tener vigente=True."""
        igv = IGVFactory(valor=Decimal("0.18"), periodo_inicio=date(2020, 1, 1), periodo_fin=None)
        assert igv.vigente is True

    def test_igv_con_periodo_fin_no_es_vigente(self):
        """IGV con periodo_fin definido debe tener vigente=False."""
        igv = IGVFactory(
            valor=Decimal("0.19"),
            periodo_inicio=date(2010, 1, 1),
            periodo_fin=date(2019, 12, 31),
        )
        assert igv.vigente is False

    def test_igv_vigente_false_cuando_tiene_periodo_fin_hoy(self):
        """IGV con periodo_fin=hoy ya no es vigente."""
        igv = IGVFactory(
            valor=Decimal("0.18"),
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=date(2026, 1, 1),
        )
        assert igv.vigente is False


@pytest.mark.django_db
class TestUITVigenteProperty:
    """Test UIT.vigente property."""

    def test_uit_sin_periodo_fin_es_vigente(self):
        """UIT sin periodo_fin debe tener vigente=True."""
        uit = UITFactory(valor=4950, periodo_inicio=date(2026, 1, 1), periodo_fin=None)
        assert uit.vigente is True

    def test_uit_con_periodo_fin_no_es_vigente(self):
        """UIT con periodo_fin definido debe tener vigente=False."""
        uit = UITFactory(
            valor=4200,
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=date(2025, 12, 31),
        )
        assert uit.vigente is False

    def test_uit_vigente_false_cuando_tiene_periodo_fin_hoy(self):
        """UIT con periodo_fin=hoy ya no es vigente."""
        uit = UITFactory(
            valor=4950,
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=date(2026, 6, 15),
        )
        assert uit.vigente is False
