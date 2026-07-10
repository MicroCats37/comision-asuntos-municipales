"""
Integration tests for Mecánica de Suelos liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest

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
    LiquidacionMecanicaSuelos,
    LiquidacionPorMetroCuadrado,
    LiquidacionProyectista,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


@pytest.mark.django_db
class TestMecanicaSuelosProyectistas:
    """Test proyectistas inline in MS creation via POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and especialidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-MS-PRO-001",
            nombre="Municipalidad de Prueba MS Proyectistas",
            distrito=self.distrito,
        )

        # Create especialidad for inline proyectistas
        self.especialidad = EspecialidadFactory()

        # Create tarifa M2 + regla for MECANICA_SUELOS
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion="MECANICA_SUELOS",
        )
        if not hasattr(self.tarifa_base, 'detalle_m2') or self.tarifa_base.detalle_m2 is None:
            TarifaPorMetroCuadradoFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_ms_con_proyectistas_vacios_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas=[] (vacío) debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-MS-PRO-001",
                    "proyectistas": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_crear_ms_con_proyectistas_inline_valido_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas inline (CIP válido, habilitado)
        debe retornar 200 y crear la asociación LiquidacionProyectista.
        """
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-MS-PRO-002",
                    "proyectistas": [
                        {
                            "cip": "000002",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "Proyectista MS de prueba",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        liquidacion_id = data["data"]["liquidacion"]["id"]

        # Verify LiquidacionProyectista was created and associated
        lp_count = LiquidacionProyectista.objects.filter(
            liquidacion_general_id=liquidacion_id
        ).count()
        assert lp_count == 1, f"Expected 1 LiquidacionProyectista, got {lp_count}"

        lp = LiquidacionProyectista.objects.get(liquidacion_general_id=liquidacion_id)
        assert lp.proyectista is not None
        assert lp.proyectista.perfil_ingeniero.cip == "000002"

    def test_crear_ms_con_cip_invalido_retorna_error(self, client: Client):
        """
        POST /primera-revision con CIP no reconocido (no existe en CIP simulator)
        debe retornar error (no 200).
        """
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-MS-PRO-003",
                    "proyectistas": [
                        {
                            "cip": "999999",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "CIP inexistente",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        # CIP no reconocido → HttpError 404 o similar (no 200)
        assert response.status_code != 200, (
            f"Expected non-200 for invalid CIP, got {response.status_code}: {response.json()}"
        )
