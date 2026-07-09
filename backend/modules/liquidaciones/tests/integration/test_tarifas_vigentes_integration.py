"""
Integration tests for GET /tarifas-vigentes endpoints (non-edificacion).

Tests the full stack for M2-type (MecanicaSuelos, HabilitacionUrbana,
ImpactoVial, Taludes) and InspeccionObra (Visitas) tariff selection endpoints.

Pattern follows test_impacto_vial_integration.py and test_inspeccion_obra_integration.py.
"""
import pytest
from decimal import Decimal

from django.test import Client

from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseM2Factory,
    TarifaLiquidacionBaseVisitasFactory,
    TarifaPorMetroCuadradoFactory,
    TarifaPorCategoriaVisitasFactory,
    ReglaTarifaLiquidacionFactory,
    ReglaTarifaInspeccionObraFactory,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TramiteAccion


@pytest.mark.django_db
class TestTarifasVigentesM2Endpoint:
    """Test GET /liquidaciones/{type}/tarifas-vigentes for M2-type liquidaciones."""

    @pytest.fixture(autouse=True)
    def setup_tarifa_m2(self):
        """Create a vigente M2 tariff with regla for PRIMERA_REVISION."""
        # TarifaM2 for MECANICA_SUELOS
        # detalle_m2 is created automatically via TarifaLiquidacionBaseM2Factory.post_generation
        self.tarifa_base =         TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
        )
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_mecanica_suelos_tarifas_vigentes_retorna_200(self, client: Client):
        """GET /liquidaciones/mecanica-suelos/tarifas-vigentes returns 200."""
        response = client.get("/api/liquidaciones/mecanica-suelos/tarifas-vigentes")
        assert response.status_code == 200, response.json()

    def test_mecanica_suelos_tarifas_vigentes_retorna_wrapper_con_tarifas(self, client: Client):
        """Response has {'data': {'tarifas': [...]}} structure."""
        response = client.get("/api/liquidaciones/mecanica-suelos/tarifas-vigentes")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]
        assert isinstance(data["data"]["tarifas"], list)

    def test_mecanica_suelos_tarifas_vigentes_retorna_tarifa_creada(self, client: Client):
        """The created tariff appears in the response."""
        response = client.get("/api/liquidaciones/mecanica-suelos/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        assert len(tarifas) >= 1
        # Find our created tariff by tarifa_id
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(self.tarifa_base.id) in tarifa_ids

    def test_mecanica_suelos_tarifas_vigentes_campos_esperados(self, client: Client):
        """Each tarifa has expected keys: tarifa_id, detalle_id, costo_por_m2, area_minima, derecho_minimo, habilitada."""
        response = client.get("/api/liquidaciones/mecanica-suelos/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        assert len(tarifas) >= 1
        tarifa = tarifas[0]
        assert "tarifa_id" in tarifa
        assert "detalle_id" in tarifa
        assert "costo_por_m2" in tarifa
        assert "area_minima" in tarifa
        assert "derecho_minimo" in tarifa
        assert "derecho_maximo" in tarifa
        assert "habilitada" in tarifa

    def test_mecanica_suelos_tarifas_vigentes_revision_distinta_accion(self, client: Client):
        """tarifas-vigentes with REVISION action returns empty (only PRIMERA_REVISION regla exists)."""
        response = client.get(
            "/api/liquidaciones/mecanica-suelos/tarifas-vigentes",
            {"tramite_accion": "REVISION"},
        )
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        # No REVISION regla exists for our tariff, so should be empty
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(self.tarifa_base.id) not in tarifa_ids

    def test_habilitacion_urbana_tarifas_vigentes_retorna_200(self, client: Client):
        """GET /liquidaciones/habilitacion-urbana/tarifas-vigentes returns 200."""
        # Create HU tariff (detalle_m2 auto-created by factory)
        hu_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA)
        ReglaTarifaLiquidacionFactory(tarifa_base=hu_base, tramite_accion=TramiteAccion.PRIMERA_REVISION)

        response = client.get("/api/liquidaciones/habilitacion-urbana/tarifas-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]

    def test_impacto_vial_tarifas_vigentes_retorna_200(self, client: Client):
        """GET /liquidaciones/impacto-vial/tarifas-vigentes returns 200."""
        # Create IV tariff (detalle_m2 auto-created by factory)
        iv_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL)
        ReglaTarifaLiquidacionFactory(tarifa_base=iv_base, tramite_accion=TramiteAccion.PRIMERA_REVISION)

        response = client.get("/api/liquidaciones/impacto-vial/tarifas-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]

    def test_taludes_tarifas_vigentes_retorna_200(self, client: Client):
        """GET /liquidaciones/taludes/tarifas-vigentes returns 200."""
        # Create Taludes tariff (detalle_m2 auto-created by factory)
        taludes_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion=TipoLiquidacion.TALUDES)
        ReglaTarifaLiquidacionFactory(tarifa_base=taludes_base, tramite_accion=TramiteAccion.PRIMERA_REVISION)

        response = client.get("/api/liquidaciones/taludes/tarifas-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]


@pytest.mark.django_db
class TestTarifasVigentesInspeccionObraEndpoint:
    """Test GET /liquidaciones/inspeccion-obra/tarifas-vigentes."""

    @pytest.fixture(autouse=True)
    def setup_tarifa_visitas(self):
        """Create a vigente InspeccionObra tariff with regla for PRIMERA_REVISION + categoria A."""
        # detalle_visitas is created automatically via TarifaLiquidacionBaseVisitasFactory.post_generation
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(
            tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA,
        )
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_inspeccion_obra_tarifas_vigentes_retorna_200(self, client: Client):
        """GET /liquidaciones/inspeccion-obra/tarifas-vigentes returns 200."""
        response = client.get("/api/liquidaciones/inspeccion-obra/tarifas-vigentes")
        assert response.status_code == 200, response.json()

    def test_inspeccion_obra_tarifas_vigentes_retorna_wrapper_con_tarifas(self, client: Client):
        """Response has {'data': {'tarifas': [...]}} structure."""
        response = client.get("/api/liquidaciones/inspeccion-obra/tarifas-vigentes")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]
        assert isinstance(data["data"]["tarifas"], list)

    def test_inspeccion_obra_tarifas_vigentes_retorna_tarifa_creada(self, client: Client):
        """The created tariff appears in the response."""
        response = client.get("/api/liquidaciones/inspeccion-obra/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(self.tarifa_base.id) in tarifa_ids

    def test_inspeccion_obra_tarifas_vigentes_campos_esperados(self, client: Client):
        """Each tarifa has expected keys: tarifa_id, detalle_id, costo_por_visita, visitas_minimas, categoria, habilitada."""
        response = client.get("/api/liquidaciones/inspeccion-obra/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        assert len(tarifas) >= 1
        tarifa = tarifas[0]
        assert "tarifa_id" in tarifa
        assert "detalle_id" in tarifa
        assert "costo_por_visita" in tarifa
        assert "visitas_minimas" in tarifa
        assert "categoria" in tarifa
        assert "habilitada" in tarifa

    def test_inspeccion_obra_tarifas_vigentes_filtra_por_categoria(self, client: Client):
        """tarifas-vigentes?categoria=A returns only categoria A tariffs."""
        # Create a B categoria tariff (detalle_visitas auto-created by factory)
        tarifa_b_base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA)
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=tarifa_b_base,
            categoria='B',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        response = client.get(
            "/api/liquidaciones/inspeccion-obra/tarifas-vigentes",
            {"categoria": "A"},
        )
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        categorias = {t["categoria"] for t in tarifas}
        assert categorias == {"A"}

    def test_inspeccion_obra_tarifas_vigentes_categoria_b_returns_b(self, client: Client):
        """tarifas-vigentes?categoria=B returns only categoria B tariffs."""
        # Create a B categoria tariff (detalle_visitas auto-created by factory)
        tarifa_b_base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA)
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=tarifa_b_base,
            categoria='B',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        response = client.get(
            "/api/liquidaciones/inspeccion-obra/tarifas-vigentes",
            {"categoria": "B"},
        )
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        categorias = {t["categoria"] for t in tarifas}
        assert categorias == {"B"}

    def test_inspeccion_obra_tarifas_vigentes_sin_categoria_retorna_todas(self, client: Client):
        """Without categoria param, returns tariffs from all categories."""
        # Create a B categoria tariff (detalle_visitas auto-created by factory)
        tarifa_b_base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA)
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=tarifa_b_base,
            categoria='B',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        response = client.get("/api/liquidaciones/inspeccion-obra/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        categorias = {t["categoria"] for t in tarifas}
        assert "A" in categorias
        assert "B" in categorias
