"""
Integration tests for GET /api/entidades/municipalidades endpoint.
"""
import pytest
from django.test import Client

from modules.entidades.domain.models import Municipalidad, MunicipalidadDistrital, MunicipalidadProvincial
from modules.entidades.tests.factories.ubigeo_factory import (
    UbigeoDepartamentoFactory,
    UbigeoDistritoFactory,
    UbigeoProvinciaFactory,
)


@pytest.mark.django_db
class TestObtenerMunicipalidadesEndpoint:
    """Test GET /api/entidades/municipalidades endpoint."""

    def test_get_municipalidades_returns_200_with_selector_items(self, client: Client):
        """GET /api/entidades/municipalidades should return id, nombre, codigo, provincia, distrito."""
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        distrito = UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")

        municipalidad_provincial = MunicipalidadProvincial.objects.create(
            codigo="MP001",
            nombre="Municipalidad Provincial de Lima",
            provincia=prov,
        )
        municipalidad_distrital = MunicipalidadDistrital.objects.create(
            codigo="MD001",
            nombre="Municipalidad Distrital de Miraflores",
            distrito=distrito,
        )

        response = client.get("/api/entidades/municipalidades")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

        # Build lookup by codigo
        by_codigo = {item["codigo"]: item for item in data["data"]}

        # Verify provincial municipalidad
        prov_item = by_codigo["MP001"]
        assert prov_item["id"] == str(municipalidad_provincial.id)
        assert prov_item["nombre"] == "Municipalidad Provincial de Lima"
        assert prov_item["codigo"] == "MP001"
        assert prov_item["provincia"] is not None
        assert prov_item["provincia"]["id"] == str(prov.id)
        assert prov_item["provincia"]["nombre"] == "LIMA"
        assert prov_item["distrito"] is None

        # Verify distrital municipalidad
        dist_item = by_codigo["MD001"]
        assert dist_item["id"] == str(municipalidad_distrital.id)
        assert dist_item["nombre"] == "Municipalidad Distrital de Miraflores"
        assert dist_item["codigo"] == "MD001"
        assert dist_item["provincia"] is None
        assert dist_item["distrito"] is not None
        assert dist_item["distrito"]["id"] == str(distrito.id)
        assert dist_item["distrito"]["nombre"] == "MIRAFLORES"

    def test_get_municipalidades_includes_keys_even_when_null(self, client: Client):
        """Keys provincia/distrito should always be present (null when not applicable)."""
        depto = UbigeoDepartamentoFactory(nombre="ANCASH")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="HUARAZ")

        # Provincial without distrito
        municipalidad_provincial = MunicipalidadProvincial.objects.create(
            codigo="MP002",
            nombre="Municipalidad Provincial de Huaraz",
            provincia=prov,
        )

        response = client.get("/api/entidades/municipalidades")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Find our item
        items = [item for item in data["data"] if item["codigo"] == "MP002"]
        assert len(items) == 1
        item = items[0]

        # Keys should exist even when null
        assert "provincia" in item
        assert "distrito" in item
        assert item["provincia"] is not None
        assert item["distrito"] is None

    def test_get_municipalidades_returns_items_without_ubigeo_linkage(self, client: Client):
        """Municipalidades with null provincia and distrito (seed data scenario) should still appear.

        This test reproduces the real seed data scenario where load_delegados_reales creates
        municipalidades with provincia=null and distrito=null. The endpoint should still
        return them with null province/distrito fields.
        """
        # Create municipalidades without ubigeo linkage (matches real seed data)
        muni1 = Municipalidad.objects.create(
            codigo="MUN0001",
            nombre="CERCADO DE LIMA",
            provincia=None,
            distrito=None,
            activo=True,
        )
        muni2 = Municipalidad.objects.create(
            codigo="MUN0002",
            nombre="ANCON",
            provincia=None,
            distrito=None,
            activo=True,
        )

        response = client.get("/api/entidades/municipalidades")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 2, "Should return municipalidades even without ubigeo linkage"

        # Find our items
        by_codigo = {item["codigo"]: item for item in data["data"]}

        # Verify first municipalidad
        item1 = by_codigo.get("MUN0001")
        assert item1 is not None, "MUN0001 should be in response"
        assert item1["nombre"] == "CERCADO DE LIMA"
        assert item1["codigo"] == "MUN0001"
        assert item1["provincia"] is None
        assert item1["distrito"] is None

        # Verify second municipalidad
        item2 = by_codigo.get("MUN0002")
        assert item2 is not None, "MUN0002 should be in response"
        assert item2["nombre"] == "ANCON"
        assert item2["provincia"] is None
        assert item2["distrito"] is None
