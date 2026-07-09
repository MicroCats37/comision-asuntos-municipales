"""
Integration tests for Impacto Vial liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest
from decimal import Decimal

from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseM2Factory,
    TarifaPorMetroCuadradoFactory,
    ReglaTarifaLiquidacionFactory,
)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionImpactoVial,
    LiquidacionPorMetroCuadrado,
)


@pytest.mark.django_db
class TestImpactoVialEndpoint:
    """Test POST /api/liquidaciones/impacto-vial/ endpoint."""

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
            codigo="MUN-IV-001",
            nombre="Municipalidad de Prueba IV",
            distrito=self.distrito,
        )

        # Create tarifa M2 + regla for IMPACTO_VIAL
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion="IMPACTO_VIAL",
        )
        if not hasattr(self.tarifa_base, 'detalle_m2') or self.tarifa_base.detalle_m2 is None:
            TarifaPorMetroCuadradoFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_impacto_vial_retorna_200(self, client: Client):
        """
        POST /api/liquidaciones/impacto-vial/primera-revision debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                    "expediente": "EXP-IV-001",
                    "observacion": "Test Impacto Vial",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_impacto_vial_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionGeneral.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_crea_liquidacion_impacto_vial(self, client: Client):
        """
        POST debe crear LiquidacionImpactoVial.
        """
        count_before = LiquidacionImpactoVial.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionImpactoVial.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_crea_liquidacion_por_m2(self, client: Client):
        """
        POST debe crear LiquidacionPorMetroCuadrado.
        """
        count_before = LiquidacionPorMetroCuadrado.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionPorMetroCuadrado.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_respuesta_tiene_estructura_correcta(self, client: Client):
        """
        La respuesta debe tener la estructura correcta con liquidacion, totales, etc.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        assert "liquidacion" in snapshot
        assert "tipo_liquidacion" in snapshot
        assert snapshot["tipo_liquidacion"] == "IMPACTO_VIAL"
        assert "totales" in snapshot
        assert "subtotal" in snapshot["totales"]
