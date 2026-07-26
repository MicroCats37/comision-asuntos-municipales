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
    LiquidacionProyectista,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


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
        La respuesta debe tener la estructura correcta con flat list item:
        id, public_id, tipo_liquidacion, estado, fecha_registro,
        proyecto, municipalidad, valores{subtotal,igv,total,total_a_pagar},
        revisiones[0]{tarifa{costo_por_visita,cantidad_visitas,categoria}}.
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

        # Flat list item structure
        assert "id" in snapshot
        assert "public_id" in snapshot
        assert "tipo_liquidacion" in snapshot
        assert snapshot["tipo_liquidacion"] == "inspeccion-obra"
        assert "estado" in snapshot
        assert "fecha_registro" in snapshot
        # proyecto nested
        assert "proyecto" in snapshot
        assert "nombre" in snapshot["proyecto"]
        # municipalidad
        assert "municipalidad" in snapshot
        assert "nombre" in snapshot["municipalidad"]
        # valores financieros
        valores = snapshot["valores"]
        assert valores["subtotal"] > 0
        assert valores["igv"] > 0
        assert valores["total"] > valores["subtotal"]
        assert valores["total_a_pagar"] == valores["total"]
        # Revision con tarifa de visitas
        assert "revisiones" in snapshot
        assert len(snapshot["revisiones"]) > 0
        tarifa = snapshot["revisiones"][0]["tarifa"]
        assert tarifa is not None
        assert "costo_por_visita" in tarifa
        assert "cantidad_visitas" in tarifa
        assert "categoria" in tarifa
        assert tarifa["categoria"] == "A"


@pytest.mark.django_db
class TestInspeccionObraProyectistas:
    """Test proyectistas inline in IO creation via POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and especialidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-PRO-001",
            nombre="Municipalidad de Prueba IO Proyectistas",
            distrito=self.distrito,
        )

        # Create especialidad for inline proyectistas
        self.especialidad = EspecialidadFactory()

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

    def test_crear_io_con_proyectistas_vacios_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas=[] (vacío) debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-001",
                    "proyectistas": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_crear_io_con_proyectistas_inline_valido_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas inline (CIP válido, habilitado)
        debe retornar 200 y crear la asociación LiquidacionProyectista.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-002",
                    "proyectistas": [
                        {
                            "cip": "000001",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "Proyectista de prueba",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        # Flat list item response: data.data is the LiquidacionIOListItemOut directly
        liquidacion_id = data["data"]["id"]

        # Verify LiquidacionProyectista was created and associated
        lp_count = LiquidacionProyectista.objects.filter(
            liquidacion_general_id=liquidacion_id
        ).count()
        assert lp_count == 1, f"Expected 1 LiquidacionProyectista, got {lp_count}"

        lp = LiquidacionProyectista.objects.get(liquidacion_general_id=liquidacion_id)
        assert lp.proyectista is not None
        assert lp.proyectista.perfil_ingeniero.cip == "000001"

    def test_crear_io_con_cip_invalido_retorna_error(self, client: Client):
        """
        POST /primera-revision con CIP no reconocido (no existe en CIP simulator)
        debe retornar error (no 200).
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-003",
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
