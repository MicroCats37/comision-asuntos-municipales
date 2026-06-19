"""
Integration tests for Finanzas GET /variables/vigentes endpoint.

Tests the full stack: controller -> orchestrator -> core -> DB.
"""
import pytest
from django.test import Client

from modules.finanzas.tests.factories.igv_factory import IGVFactory
from modules.finanzas.tests.factories.uit_factory import UITFactory


@pytest.mark.django_db
class TestVariablesVigentesEndpoint:
    """Test GET /api/finanzas/variables/vigentes endpoint."""

    def setup_method(self):
        """Seed IGV y UIT vigentes antes de cada test."""
        self.igv = IGVFactory(valor="0.18", periodo_inicio="2020-01-01")
        self.uit = UITFactory(valor=4950, periodo_inicio="2026-01-01")

    def test_get_variables_vigentes_retorna_200_con_igv_y_uit(self, client: Client):
        """GET /api/finanzas/variables/vigentes debe retornar 200 con igv y uit."""
        response = client.get("/api/finanzas/variables/vigentes")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["igv_valor"] == pytest.approx(0.18)
        assert data["data"]["uit_valor"] == pytest.approx(4950.0)
        assert data["data"]["igv_periodo_inicio"] == "2020-01-01"
        assert data["data"]["uit_periodo_inicio"] == "2026-01-01"

    def test_get_variables_vigentes_sin_datos_retorna_defaults(self, client: Client):
        """Sin IGV/UIT en DB, el endpoint debe retornar defaults (0.18 y 0)."""
        from modules.finanzas.models import IGV, UIT
        IGV.objects.all().delete()
        UIT.objects.all().delete()

        response = client.get("/api/finanzas/variables/vigentes")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["igv_valor"] == pytest.approx(0.18)
        assert data["data"]["uit_valor"] == 0.0
