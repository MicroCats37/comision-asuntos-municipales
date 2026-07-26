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
    ReglaTarifaEdificacionFactory,
    ReglaTarifaInspeccionObraFactory,
)
from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import (
    TarifaLiquidacionBaseFactory,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones, TramiteAccion


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
        """Each tarifa has expected keys: tarifa_id, detalle_id, costo_por_m2, area_m2, derecho_minimo, habilitada."""
        response = client.get("/api/liquidaciones/mecanica-suelos/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        assert len(tarifas) >= 1
        tarifa = tarifas[0]
        assert "tarifa_id" in tarifa
        assert "detalle_id" in tarifa
        assert "costo_por_m2" in tarifa
        assert "area_m2" in tarifa
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


@pytest.mark.django_db
class TestTarifasVigentesIVTaludesPorcentajeEndpoint:
    """
    Test GET /liquidaciones/impacto-vial/tarifas-vigentes and
    GET /liquidaciones/taludes/tarifas-vigentes for percentage-of-obra tariffs.

    These endpoints now query ReglaTarifaEdificacion (not ReglaTarifaLiquidacion)
    to match the seed data pattern. IV/Taludes use OBRA_NUEVA as placeholder
    tipo_tramite since they don't have tipo_tramite in their domain.

    Verifies the fix for the seed/core mismatch bug.
    """

    @pytest.fixture(autouse=True)
    def setup_iv_tarifa_porcentaje(self):
        """Create IV percentage tariff with ReglaTarifaEdificacion (OBRA_NUEVA placeholder)."""
        # Create percentage tariff for IMPACTO_VIAL
        # TarifaLiquidacionBaseFactory auto-creates TarifaPorcentajeObra via post_generation
        self.iv_base = TarifaLiquidacionBaseFactory(
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
            periodo_inicio="2020-01-01",
            periodo_fin=None,
        )
        # Override auto-created percentage values
        self.iv_base.detalle_porcentual.porcentaje_liquidacion = Decimal("0.0015")
        self.iv_base.detalle_porcentual.derecho_minimo = Decimal("110.00")
        self.iv_base.detalle_porcentual.porcentaje_minimo_uit = Decimal("0.02")
        self.iv_base.detalle_porcentual.save()
        # Add especialidades
        esp = EspecialidadFactory(nombre="Ingenieria Civil")
        self.iv_base.especialidades.add(esp)
        # Create ReglaTarifaEdificacion with OBRA_NUEVA placeholder tipo_tramite
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.iv_base,
        )

    @pytest.fixture
    def setup_taludes_tarifa_porcentaje(self):
        """Create Taludes percentage tariff with ReglaTarifaEdificacion."""
        # TarifaLiquidacionBaseFactory auto-creates TarifaPorcentajeObra via post_generation
        taludes_base = TarifaLiquidacionBaseFactory(
            tipo_liquidacion=TipoLiquidacion.TALUDES,
            periodo_inicio="2020-01-01",
            periodo_fin=None,
        )
        # Override auto-created percentage values
        taludes_base.detalle_porcentual.porcentaje_liquidacion = Decimal("0.0015")
        taludes_base.detalle_porcentual.derecho_minimo = Decimal("110.00")
        taludes_base.detalle_porcentual.porcentaje_minimo_uit = Decimal("0.02")
        taludes_base.detalle_porcentual.save()
        # Use different specialty name to avoid conflict with IV fixture
        esp = EspecialidadFactory(nombre="Ingenieria Sanitaria")
        taludes_base.especialidades.add(esp)
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=taludes_base,
        )
        return taludes_base

    def test_impacto_vial_tarifas_vigentes_usa_regla_tarifa_edificacion(self, client: Client):
        """
        GET /liquidaciones/impacto-vial/tarifas-vigentes returns the tariff
        created via ReglaTarifaEdificacion (OBRA_NUEVA placeholder).
        """
        response = client.get("/api/liquidaciones/impacto-vial/tarifas-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]
        tarifas = data["data"]["tarifas"]
        assert len(tarifas) >= 1, "IV tariff should be returned when using ReglaTarifaEdificacion"
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(self.iv_base.id) in tarifa_ids

    def test_impacto_vial_tarifas_vigentes_con_regla_liquidacion_retorna_vacio(self, client: Client):
        """
        When only ReglaTarifaLiquidacion exists (old pattern), IV endpoint returns empty.
        This confirms the endpoint now queries ReglaTarifaEdificacion, not ReglaTarifaLiquidacion.
        """
        # Create tariff with ReglaTarifaLiquidacion only (old pattern - should NOT be returned)
        iv_base_old = TarifaLiquidacionBaseFactory(
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
            periodo_inicio="2020-01-01",
            periodo_fin=None,
        )
        # Override auto-created percentage values
        iv_base_old.detalle_porcentual.porcentaje_liquidacion = Decimal("0.0015")
        iv_base_old.detalle_porcentual.derecho_minimo = Decimal("110.00")
        iv_base_old.detalle_porcentual.porcentaje_minimo_uit = Decimal("0.02")
        iv_base_old.detalle_porcentual.save()
        ReglaTarifaLiquidacionFactory(
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=iv_base_old,
        )

        response = client.get("/api/liquidaciones/impacto-vial/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        # Old pattern (ReglaTarifaLiquidacion) should NOT be returned
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(iv_base_old.id) not in tarifa_ids

    def test_taludes_tarifas_vigentes_usa_regla_tarifa_edificacion(self, client: Client, setup_taludes_tarifa_porcentaje):
        """
        GET /liquidaciones/taludes/tarifas-vigentes returns the tariff
        created via ReglaTarifaEdificacion (OBRA_NUEVA placeholder).
        """
        response = client.get("/api/liquidaciones/taludes/tarifas-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "tarifas" in data["data"]
        tarifas = data["data"]["tarifas"]
        assert len(tarifas) >= 1, "Taludes tariff should be returned when using ReglaTarifaEdificacion"
        tarifa_ids = [t["tarifa_id"] for t in tarifas]
        assert str(setup_taludes_tarifa_porcentaje.id) in tarifa_ids

    def test_iv_tarifas_vigentes_campos_porcentaje(self, client: Client):
        """Percentage tariff response includes expected percentage fields."""
        response = client.get("/api/liquidaciones/impacto-vial/tarifas-vigentes")
        assert response.status_code == 200
        tarifas = response.json()["data"]["tarifas"]
        assert len(tarifas) >= 1
        tarifa = tarifas[0]
        # Percentage tariff fields
        assert "porcentaje_liquidacion" in tarifa
        assert "porcentaje_minimo_uit" in tarifa
        assert "derecho_minimo" in tarifa
        assert "habilitada" in tarifa
        # NOT M2 fields
        assert "costo_por_m2" not in tarifa
        assert "area_m2" not in tarifa

    def test_iv_revisiones_vigentes_usa_regla_tarifa_edificacion(self, client: Client):
        """
        GET /liquidaciones/impacto-vial/revisiones-vigentes returns revisions
        via ReglaTarifaEdificacion.
        """
        response = client.get("/api/liquidaciones/impacto-vial/revisiones-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        revisiones = data["data"].get("revisiones", [])
        assert len(revisiones) >= 1, "IV revision should be returned via ReglaTarifaEdificacion"
        revision_ids = [r["id"] for r in revisiones]
        assert str(self.iv_base.id) in revision_ids

    def test_taludes_revisiones_vigentes_usa_regla_tarifa_edificacion(self, client: Client, setup_taludes_tarifa_porcentaje):
        """
        GET /liquidaciones/taludes/revisiones-vigentes returns revisions
        via ReglaTarifaEdificacion.
        """
        response = client.get("/api/liquidaciones/taludes/revisiones-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        revisiones = data["data"].get("revisiones", [])
        assert len(revisiones) >= 1, "Taludes revision should be returned via ReglaTarifaEdificacion"
        revision_ids = [r["id"] for r in revisiones]
        assert str(setup_taludes_tarifa_porcentaje.id) in revision_ids
