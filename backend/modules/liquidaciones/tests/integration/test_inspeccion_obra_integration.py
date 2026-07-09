"""
Integration tests for Inspección de Obra liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest
from decimal import Decimal

from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseVisitasFactory,
    TarifaPorCategoriaVisitasFactory,
    ReglaTarifaInspeccionObraFactory,
)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionInspeccionObra,
    LiquidacionPorCategoriaVisitas,
)


@pytest.mark.django_db
class TestInspeccionObraEndpoint:
    """Test POST /api/liquidaciones/inspeccion-obra/ endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, and municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create municipalidad
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-001",
            nombre="Municipalidad de Prueba IO",
            distrito=self.distrito,
        )

        # Create tarifa visitas + regla for INSPECCION_OBRA + categoria A
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(
            tipo_liquidacion="INSPECCION_OBRA",
        )
        if not hasattr(self.tarifa_base, 'detalle_visitas') or self.tarifa_base.detalle_visitas is None:
            TarifaPorCategoriaVisitasFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_inspeccion_obra_retorna_200(self, client: Client):
        """
        POST /api/liquidaciones/inspeccion-obra/primera-revision debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                    "expediente": "EXP-IO-001",
                    "observacion": "Test Inspeccion Obra",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_inspeccion_obra_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionGeneral.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_crea_liquidacion_inspeccion_obra(self, client: Client):
        """
        POST debe crear LiquidacionInspeccionObra.
        """
        count_before = LiquidacionInspeccionObra.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionInspeccionObra.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_crea_liquidacion_por_visitas(self, client: Client):
        """
        POST debe crear LiquidacionPorCategoriaVisitas.
        """
        count_before = LiquidacionPorCategoriaVisitas.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionPorCategoriaVisitas.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_respuesta_tiene_estructura_correcta(self, client: Client):
        """
        La respuesta debe tener la estructura correcta con liquidacion, totales, calculo_visitas.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        assert "liquidacion" in snapshot
        assert "tipo_liquidacion" in snapshot
        assert snapshot["tipo_liquidacion"] == "INSPECCION_OBRA"
        assert "totales" in snapshot
        assert "calculo_visitas" in snapshot
        assert snapshot["calculo_visitas"]["categoria"] == "A"
