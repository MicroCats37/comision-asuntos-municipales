"""
Contract tests for list endpoint tariff exposure via revisiones.

Tests that verify tariff fields are exposed in revisiones[n].tarifa
instead of the removed `detalle` field.

For M2 types (MS, HU, IV, Taludes): verifies costo_por_m2, area_m2, derecho_minimo, derecho_maximo.
For IO: verifies costo_por_visita, visitas_minimas, categoria.
"""
import pytest
from decimal import Decimal

from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseM2Factory,
    TarifaLiquidacionBaseVisitasFactory,
    TarifaPorMetroCuadradoFactory,
    TarifaPorCategoriaVisitasFactory,
    ReglaTarifaLiquidacionFactory,
    ReglaTarifaInspeccionObraFactory,
    ReglaTarifaEdificacionFactory,
)
from modules.liquidaciones.tests.factories.especialidades_liquidacion_factory import EspecialidadesLiquidacionFactory
from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import (
    TarifaLiquidacionBaseFactory,
)


@pytest.mark.django_db
class TestGeneralListNoDetalle:
    """Test that general `/liquidaciones/` endpoint does NOT expose `detalle`."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and MS tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-001",
            nombre="Municipalidad de Prueba",
            distrito=self.distrito,
        )

        # Create MS/M2 tariff
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="MECANICA_SUELOS")
        ReglaTarifaLiquidacionFactory(tarifa_base=self.tarifa_base)

    def test_general_list_no_detalle_field(self, client: Client):
        """
        GET /api/liquidaciones/ response must NOT have `detalle` field in items.
        Tariff data is now in revisiones[n].tarifa.
        """
        # Create a liquidacion via MS API (to properly set all fields)
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "observacion": "Test MS Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Now query general endpoint
        response = client.get("/api/liquidaciones/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        assert "data" in data
        assert "items" in data["data"]

        # Find our MS liquidacion in the list
        ms_items = [i for i in data["data"]["items"] if i.get("tipo_liquidacion") == "mecanica-suelos"]
        assert len(ms_items) >= 1, "Expected at least 1 MS liquidacion in general list"

        item = ms_items[0]
        # Contract: detalle must NOT be present in general list item
        assert "detalle" not in item, (
            f"General endpoint must not expose `detalle`. Keys found: {list(item.keys())}"
        )
        # Tariff data must be in revisiones
        assert "revisiones" in item, "revisiones must be present"
        assert len(item["revisiones"]) >= 1, "Expected at least 1 revision"
        assert item["revisiones"][0].get("tarifa") is not None, "tarifa must be present in revision"


@pytest.mark.django_db
class TestMSListTarifaContract:
    """Test that MS `/liquidaciones/mecanica-suelos/` endpoint exposes tariff in revisiones."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and MS tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-MS-001",
            nombre="Municipalidad de Prueba MS",
            distrito=self.distrito,
        )

        # Create MS/M2 tariff
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="MECANICA_SUELOS")
        ReglaTarifaLiquidacionFactory(tarifa_base=self.tarifa_base)

    def test_ms_list_has_revisiones_with_tariff(self, client: Client):
        """MS list response must have revisiones with tariff data."""
        # Create MS liquidacion via API
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "observacion": "Test MS Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query MS list endpoint
        response = client.get("/api/liquidaciones/mecanica-suelos/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        assert "data" in data
        assert "items" in data["data"]

        assert len(data["data"]["items"]) == 1, "Expected 1 MS liquidacion"
        item = data["data"]["items"][0]

        # Contract: revisiones must be present with tariff
        assert "revisiones" in item, f"MS endpoint must expose revisiones. Keys: {list(item.keys())}"
        assert len(item["revisiones"]) >= 1, "Expected at least 1 revision"
        revision = item["revisiones"][0]
        assert "tarifa" in revision, "revision must have tarifa"
        assert revision["tarifa"] is not None, "tarifa must not be None"

    def test_ms_list_tarifa_has_m2_fields(self, client: Client):
        """MS tarifa must have M2 fields: costo_por_m2, area_m2, derecho_minimo, derecho_maximo."""
        # Create MS liquidacion via API
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "observacion": "Test MS Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query MS list endpoint
        response = client.get("/api/liquidaciones/mecanica-suelos/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # M2 tariff fields must have real values
        assert tarifa["costo_por_m2"] is not None, (
            "costo_por_m2 must not be null for MS revision — tariff data is missing or not linked"
        )
        assert tarifa["costo_por_m2"] > 0, (
            f"costo_por_m2 must be a positive number, got: {tarifa['costo_por_m2']}"
        )
        assert tarifa["area_m2"] is not None, "area_m2 must not be null"
        assert tarifa["derecho_minimo"] is not None, (
            "derecho_minimo must not be null for MS revision"
        )
        assert tarifa["derecho_minimo"] > 0, (
            f"derecho_minimo must be a positive number, got: {tarifa['derecho_minimo']}"
        )


@pytest.mark.django_db
class TestIOListTarifaContract:
    """Test that IO `/liquidaciones/inspeccion-obra/` endpoint exposes tariff in revisiones."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and IO tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-001",
            nombre="Municipalidad de Prueba IO",
            distrito=self.distrito,
        )

        # Create IO tariff
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion="INSPECCION_OBRA")
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
        )

    def test_io_list_has_revisiones_with_tariff(self, client: Client):
        """IO list response must have revisiones with tariff data."""
        # Create IO liquidacion via API
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                    "observacion": "Test IO Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query IO list endpoint
        response = client.get("/api/liquidaciones/inspeccion-obra/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        assert "data" in data
        assert "items" in data["data"]

        assert len(data["data"]["items"]) == 1, "Expected 1 IO liquidacion"
        item = data["data"]["items"][0]

        # Contract: revisiones must be present with tariff
        assert "revisiones" in item
        assert len(item["revisiones"]) >= 1
        revision = item["revisiones"][0]
        assert "tarifa" in revision
        assert revision["tarifa"] is not None

    def test_io_list_tarifa_has_io_fields(self, client: Client):
        """IO tarifa must have IO fields: costo_por_visita, visitas_minimas, categoria."""
        # Create IO liquidacion via API
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                    "observacion": "Test IO Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query IO list endpoint
        response = client.get("/api/liquidaciones/inspeccion-obra/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # IO tariff fields must have real values
        assert tarifa["costo_por_visita"] is not None, (
            "costo_por_visita must not be null for IO revision — tariff data is missing or not linked"
        )
        assert tarifa["costo_por_visita"] > 0, (
            f"costo_por_visita must be a positive number, got: {tarifa['costo_por_visita']}"
        )
        assert tarifa["visitas_minimas"] is not None, (
            "visitas_minimas must not be null for IO revision"
        )
        assert tarifa["categoria"] is not None and tarifa["categoria"] != "", (
            f"categoria must be a non-empty string for IO revision, got: {tarifa['categoria']}"
        )


@pytest.mark.django_db
class TestHUListTarifaContract:
    """Test that HU `/liquidaciones/habilitacion-urbana/` endpoint exposes tariff in revisiones."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and HU tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-HU-001",
            nombre="Municipalidad de Prueba HU",
            distrito=self.distrito,
        )

        # Create HU/M2 tariff

        # Create HU/M2 tariff
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="HABILITACION_URBANA")
        ReglaTarifaLiquidacionFactory(tarifa_base=self.tarifa_base)

    def test_hu_list_tarifa_has_m2_fields(self, client: Client):
        """HU tarifa must have M2 fields."""
        # Create HU liquidacion via API
        response = client.post(
            "/api/liquidaciones/habilitacion-urbana/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                    "observacion": "Test HU Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query HU list endpoint
        response = client.get("/api/liquidaciones/habilitacion-urbana/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        assert tarifa["costo_por_m2"] is not None, (
            "costo_por_m2 must not be null for HU revision"
        )
        assert tarifa["costo_por_m2"] > 0
        assert tarifa["derecho_minimo"] is not None
        assert tarifa["derecho_minimo"] > 0


@pytest.mark.django_db
class TestIVListTarifaContract:
    """Test that IV `/liquidaciones/impacto-vial/` endpoint exposes tariff in revisiones."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and IV tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IV-001",
            nombre="Municipalidad de Prueba IV",
            distrito=self.distrito,
        )

        # Create IV/M2 tariff
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="IMPACTO_VIAL")
        ReglaTarifaLiquidacionFactory(tarifa_base=self.tarifa_base)

    def test_iv_list_tarifa_has_m2_fields(self, client: Client):
        """IV tarifa must have M2 fields."""
        # Create IV liquidacion via API
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 200.0,
                    "observacion": "Test IV Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query IV list endpoint
        response = client.get("/api/liquidaciones/impacto-vial/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        assert tarifa["costo_por_m2"] is not None
        assert tarifa["costo_por_m2"] > 0
        assert tarifa["derecho_minimo"] is not None
        assert tarifa["derecho_minimo"] > 0


@pytest.mark.django_db
class TestTaludesListTarifaContract:
    """Test that Taludes `/liquidaciones/taludes/` endpoint exposes tariff in revisiones."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and Taludes tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TAL-001",
            nombre="Municipalidad de Prueba Taludes",
            distrito=self.distrito,
        )

        # Create Taludes/M2 tariff
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="TALUDES")
        ReglaTarifaLiquidacionFactory(tarifa_base=self.tarifa_base)

    def test_taludes_list_tarifa_has_m2_fields(self, client: Client):
        """Taludes tarifa must have M2 fields."""
        # Create Taludes liquidacion via API
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 180.0,
                    "observacion": "Test Taludes Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query Taludes list endpoint
        response = client.get("/api/liquidaciones/taludes/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        assert tarifa["costo_por_m2"] is not None
        assert tarifa["costo_por_m2"] > 0
        assert tarifa["derecho_minimo"] is not None
        assert tarifa["derecho_minimo"] > 0


@pytest.mark.django_db
class TestTariffValuesInRevisiones:
    """
    Verify that tariff values exposed in revisiones match the actual seeded tariff data.

    Factories create tariff sub-objects with specific values:
    - TarifaPorMetroCuadradoFactory: costo_por_m2=50.0000, derecho_minimo=500.00, derecho_maximo=5000.00
    - TarifaPorCategoriaVisitasFactory: costo_por_visita=150.00, visitas_minimas=1
    - TarifaPorcentajeObraFactory: porcentaje_liquidacion=0.05 (5%), derecho_minimo=500.00

    These tests FAIL if the API returns null/0 for tariff fields instead of the seeded values.
    """

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and tariffs with KNOWN values."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TAR-001",
            nombre="Municipalidad de Prueba Tarifas",
            distrito=self.distrito,
        )

    def test_ms_tariff_values_match_seeded(self, client: Client):
        """
        MS revisiones[n].tarifa.costo_por_m2 and derecho_minimo must match TarifaPorMetroCuadrado seeded values.
        """
        from modules.liquidaciones.models import TarifaPorMetroCuadrado

        # Create MS/M2 tariff with factory defaults
        tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="MECANICA_SUELOS")
        ReglaTarifaLiquidacionFactory(tarifa_base=tarifa_base)

        # Get the seeded tariff sub-object
        tarifa_m2 = TarifaPorMetroCuadrado.objects.get(tarifa_base=tarifa_base)
        expected_costo_m2 = float(tarifa_m2.costo_por_m2)
        expected_derecho_minimo = float(tarifa_m2.derecho_minimo)

        # Create MS liquidacion via API
        response = client.post(
            "/api/liquidaciones/mecanica-suelos/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "observacion": "Test Tariff Values MS",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query MS list endpoint
        response = client.get("/api/liquidaciones/mecanica-suelos/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["costo_por_m2"] == expected_costo_m2, (
            f"costo_por_m2 should be {expected_costo_m2} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['costo_por_m2']}"
        )
        assert tarifa["derecho_minimo"] == expected_derecho_minimo, (
            f"derecho_minimo should be {expected_derecho_minimo} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['derecho_minimo']}"
        )

    def test_io_tariff_values_match_seeded(self, client: Client):
        """
        IO revisiones[n].tarifa.costo_por_visita and visitas_minimas must match seeded values.
        """
        from modules.liquidaciones.models import TarifaPorCategoriaVisitas

        # Create IO tariff with factory defaults
        tarifa_base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion="INSPECCION_OBRA")
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=tarifa_base,
            categoria='A',
        )

        # Get the seeded tariff sub-object
        tarifa_visitas = TarifaPorCategoriaVisitas.objects.get(tarifa_base=tarifa_base)
        expected_costo_por_visita = float(tarifa_visitas.costo_por_visita)
        expected_visitas_minimas = tarifa_visitas.visitas_minimas

        # Create IO liquidacion via API
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                    "observacion": "Test Tariff Values IO",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query IO list endpoint
        response = client.get("/api/liquidaciones/inspeccion-obra/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["costo_por_visita"] == expected_costo_por_visita, (
            f"costo_por_visita should be {expected_costo_por_visita} (from TarifaPorCategoriaVisitas), "
            f"got: {tarifa['costo_por_visita']}"
        )
        assert tarifa["visitas_minimas"] == expected_visitas_minimas, (
            f"visitas_minimas should be {expected_visitas_minimas} (from TarifaPorCategoriaVisitas), "
            f"got: {tarifa['visitas_minimas']}"
        )
        assert tarifa["categoria"] == "A", (
            f"categoria should be 'A' (from request), got: {tarifa['categoria']}"
        )

    def test_hu_tariff_values_match_seeded(self, client: Client):
        """HU revisiones[n].tarifa.costo_por_m2 must match TarifaPorMetroCuadrado seeded values."""
        from modules.liquidaciones.models import TarifaPorMetroCuadrado

        # Create HU/M2 tariff with factory defaults
        tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="HABILITACION_URBANA")
        ReglaTarifaLiquidacionFactory(tarifa_base=tarifa_base)

        # Get the seeded tariff sub-object
        tarifa_m2 = TarifaPorMetroCuadrado.objects.get(tarifa_base=tarifa_base)
        expected_costo_m2 = float(tarifa_m2.costo_por_m2)
        expected_derecho_minimo = float(tarifa_m2.derecho_minimo)

        # Create HU liquidacion via API
        response = client.post(
            "/api/liquidaciones/habilitacion-urbana/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                    "observacion": "Test Tariff Values HU",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query HU list endpoint
        response = client.get("/api/liquidaciones/habilitacion-urbana/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["costo_por_m2"] == expected_costo_m2, (
            f"costo_por_m2 should be {expected_costo_m2} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['costo_por_m2']}"
        )
        assert tarifa["derecho_minimo"] == expected_derecho_minimo, (
            f"derecho_minimo should be {expected_derecho_minimo} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['derecho_minimo']}"
        )

    def test_iv_tariff_values_match_seeded(self, client: Client):
        """IV revisiones[n].tarifa.costo_por_m2 must match TarifaPorMetroCuadrado seeded values."""
        from modules.liquidaciones.models import TarifaPorMetroCuadrado

        # Create IV/M2 tariff with factory defaults
        tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="IMPACTO_VIAL")
        ReglaTarifaLiquidacionFactory(tarifa_base=tarifa_base)

        # Get the seeded tariff sub-object
        tarifa_m2 = TarifaPorMetroCuadrado.objects.get(tarifa_base=tarifa_base)
        expected_costo_m2 = float(tarifa_m2.costo_por_m2)
        expected_derecho_minimo = float(tarifa_m2.derecho_minimo)

        # Create IV liquidacion via API
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 200.0,
                    "observacion": "Test Tariff Values IV",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query IV list endpoint
        response = client.get("/api/liquidaciones/impacto-vial/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["costo_por_m2"] == expected_costo_m2, (
            f"costo_por_m2 should be {expected_costo_m2} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['costo_por_m2']}"
        )
        assert tarifa["derecho_minimo"] == expected_derecho_minimo, (
            f"derecho_minimo should be {expected_derecho_minimo} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['derecho_minimo']}"
        )

    def test_taludes_tariff_values_match_seeded(self, client: Client):
        """Taludes revisiones[n].tarifa.costo_por_m2 must match TarifaPorMetroCuadrado seeded values."""
        from modules.liquidaciones.models import TarifaPorMetroCuadrado

        # Create Taludes/M2 tariff with factory defaults
        tarifa_base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion="TALUDES")
        ReglaTarifaLiquidacionFactory(tarifa_base=tarifa_base)

        # Get the seeded tariff sub-object
        tarifa_m2 = TarifaPorMetroCuadrado.objects.get(tarifa_base=tarifa_base)
        expected_costo_m2 = float(tarifa_m2.costo_por_m2)
        expected_derecho_minimo = float(tarifa_m2.derecho_minimo)

        # Create Taludes liquidacion via API
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 180.0,
                    "observacion": "Test Tariff Values Taludes",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query Taludes list endpoint
        response = client.get("/api/liquidaciones/taludes/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["costo_por_m2"] == expected_costo_m2, (
            f"costo_por_m2 should be {expected_costo_m2} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['costo_por_m2']}"
        )
        assert tarifa["derecho_minimo"] == expected_derecho_minimo, (
            f"derecho_minimo should be {expected_derecho_minimo} (from TarifaPorMetroCuadrado), "
            f"got: {tarifa['derecho_minimo']}"
        )


@pytest.mark.django_db
class TestEdificacionListTarifaContract:
    """Test that Edificación `/liquidaciones/edificaciones/` endpoint exposes tariff with porcentaje_liquidacion."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and Edificación tariff."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        from modules.liquidaciones.domain.constants import TipoTramiteEdificaciones, TramiteAccion

        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-EDIF-001",
            nombre="Municipalidad de Prueba Edificación",
            distrito=self.distrito,
        )

        # Create Especialidad and associate with tariff (required)
        self.especialidad = EspecialidadFactory()

        # Create Edificación tariff with TarifaLiquidacionBase + TarifaPorcentajeObra + especialidades
        self.tarifa_base = TarifaLiquidacionBaseFactory(
            tipo_liquidacion="EDIFICACION",
            especialidades=[self.especialidad],
        )
        ReglaTarifaEdificacionFactory(
            tarifa_base=self.tarifa_base,
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_edificacion_list_has_revisiones_with_tariff(self, client: Client):
        """Edificación list response must have revisiones with tariff data."""
        # Create Edificación liquidacion via API
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-liquidacion",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 100000.0,
                    "valor_base_calculo": 100000.0,
                    "tarifas_ids": [str(self.tarifa_base.id)],
                    "observacion": "Test Edificación Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query Edificación list endpoint
        response = client.get("/api/liquidaciones/edificaciones/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        assert "data" in data
        assert "items" in data["data"]

        assert len(data["data"]["items"]) >= 1, "Expected at least 1 Edificación liquidacion"
        item = data["data"]["items"][0]

        # Contract: revisiones must be present with tariff
        assert "revisiones" in item, f"Edificación endpoint must expose revisiones. Keys: {list(item.keys())}"
        assert len(item["revisiones"]) >= 1, "Expected at least 1 revision"
        revision = item["revisiones"][0]
        assert "tarifa" in revision, "revision must have tarifa"
        assert revision["tarifa"] is not None, "tarifa must not be None"

    def test_edificacion_list_tarifa_has_porcentaje_liquidacion(self, client: Client):
        """Edificación tarifa must have porcentaje_liquidacion field with positive value."""
        # Create Edificación liquidacion via API
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-liquidacion",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 100000.0,
                    "valor_base_calculo": 100000.0,
                    "tarifas_ids": [str(self.tarifa_base.id)],
                    "observacion": "Test Edificación Contract",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query Edificación list endpoint
        response = client.get("/api/liquidaciones/edificaciones/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Edificación tariff fields must have real values
        assert "porcentaje_liquidacion" in tarifa, (
            "porcentaje_liquidacion must be present in Edificación tariff"
        )
        assert tarifa["porcentaje_liquidacion"] is not None, (
            "porcentaje_liquidacion must not be null for Edificación revision"
        )
        assert tarifa["porcentaje_liquidacion"] > 0, (
            f"porcentaje_liquidacion must be a positive number, got: {tarifa['porcentaje_liquidacion']}"
        )
        assert tarifa["derecho_minimo"] is not None, (
            "derecho_minimo must not be null for Edificación revision"
        )
        assert tarifa["derecho_minimo"] > 0, (
            f"derecho_minimo must be a positive number, got: {tarifa['derecho_minimo']}"
        )

    def test_edificacion_tariff_values_match_seeded(self, client: Client):
        """
        Edificación revisiones[n].tarifa.porcentaje_liquidacion must match TarifaPorcentajeObra seeded value.
        """
        from modules.liquidaciones.models import TarifaPorcentajeObra

        # Get the seeded tariff sub-object
        tarifa_pct = TarifaPorcentajeObra.objects.get(tarifa_base=self.tarifa_base)
        expected_porcentaje = float(tarifa_pct.porcentaje_liquidacion)
        expected_derecho_minimo = float(tarifa_pct.derecho_minimo)

        # Create Edificación liquidacion via API
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-liquidacion",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 100000.0,
                    "valor_base_calculo": 100000.0,
                    "tarifas_ids": [str(self.tarifa_base.id)],
                    "observacion": "Test Tariff Values Edificación",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

        # Query Edificación list endpoint
        response = client.get("/api/liquidaciones/edificaciones/", {"page": 1, "page_size": 10})
        assert response.status_code == 200, response.json()

        data = response.json()
        item = data["data"]["items"][0]
        tarifa = item["revisiones"][0]["tarifa"]

        # Verify tariff values match seeded data
        assert tarifa["porcentaje_liquidacion"] == expected_porcentaje, (
            f"porcentaje_liquidacion should be {expected_porcentaje} "
            f"(from TarifaPorcentajeObra), got: {tarifa['porcentaje_liquidacion']}"
        )
        assert tarifa["derecho_minimo"] == expected_derecho_minimo, (
            f"derecho_minimo should be {expected_derecho_minimo} "
            f"(from TarifaPorcentajeObra), got: {tarifa['derecho_minimo']}"
        )
