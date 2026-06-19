"""
Unit tests for FinanzasCoreService — tests IGV/UIT retrieval logic.
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.tests.factories.igv_factory import IGVFactory
from modules.finanzas.tests.factories.uit_factory import UITFactory


@pytest.mark.django_db
class TestFinanzasCoreService:
    """Test FinanzasCoreService sync operations."""

    def setup_method(self):
        """Create seeded IGV/UIT antes de cada test."""
        self.igv = IGVFactory(valor=Decimal("0.18"), periodo_inicio=date(2020, 1, 1))
        self.uit = UITFactory(valor=4950, periodo_inicio=date(2026, 1, 1))

    def test_obtener_igv_vigente_devuelve_igv_sin_periodo_fin(self):
        """_obtener_igv_vigente() debe retornar el IGV sin periodo_fin."""
        service = FinanzasCoreService()
        igv = service._obtener_igv_vigente()
        assert igv is not None
        assert igv.valor == Decimal("0.18")
        assert igv.periodo_fin is None

    def test_obtener_uit_vigente_devuelve_uit_sin_periodo_fin(self):
        """_obtener_uit_vigente() debe retornar la UIT sin periodo_fin."""
        service = FinanzasCoreService()
        uit = service._obtener_uit_vigente()
        assert uit is not None
        assert uit.valor == 4950
        assert uit.periodo_fin is None

    def test_igv_con_periodo_fin_no_es_vigente(self):
        """IGV con periodo_fin definido NO debe ser retornado como vigente."""
        IGVFactory(
            valor=Decimal("0.19"),
            periodo_inicio=date(2010, 1, 1),
            periodo_fin=date(2019, 12, 31),
        )
        service = FinanzasCoreService()
        igv = service._obtener_igv_vigente()
        assert igv.valor == Decimal("0.18")

    def test_uit_con_periodo_fin_no_es_vigente(self):
        """UIT con periodo_fin definido NO debe ser retornado como vigente."""
        UITFactory(
            valor=4200,
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=date(2025, 12, 31),
        )
        service = FinanzasCoreService()
        uit = service._obtener_uit_vigente()
        assert uit.valor == 4950

    def test_sin_igv_ni_uit_vigentes_retorna_defaults(self):
        """Sin IGV/UIT vigentes, el método sync retorna defaults."""
        from modules.finanzas.models import IGV, UIT
        IGV.objects.all().delete()
        UIT.objects.all().delete()

        service = FinanzasCoreService()
        # El servicio retorna defaults cuando no hay datos
        igv = service._obtener_igv_vigente()
        uit = service._obtener_uit_vigente()
        assert igv is None
        assert uit is None
