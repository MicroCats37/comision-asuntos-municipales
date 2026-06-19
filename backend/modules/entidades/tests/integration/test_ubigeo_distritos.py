"""
Integration tests for GET /api/entidades/ubigeo/distritos endpoint.
"""
import pytest
from django.test import Client

from modules.entidades.tests.factories.ubigeo_factory import (
    UbigeoDepartamentoFactory,
    UbigeoProvinciaFactory,
    UbigeoDistritoFactory,
)


@pytest.mark.django_db
class TestObtenerDistritosEndpoint:
    """Test GET /api/entidades/ubigeo/distritos endpoint."""

    def test_get_distritos_returns_200_with_items_and_total(self, client: Client):
        """
        GET /api/entidades/ubigeo/distritos should return 200 with items/total structure.
        """
        # Create ubigeo hierarchy
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov, nombre="SURCO", ubigeo="150102")

        response = client.get("/api/entidades/ubigeo/distritos")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] == 2
        assert len(data["data"]["items"]) == 2

    def test_get_distritos_returns_correct_item_structure(self, client: Client):
        """
        Each item should have id, nombre, ubigeo, provincia, and departamento.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")

        response = client.get("/api/entidades/ubigeo/distritos")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        items = data["data"]["items"]
        assert len(items) == 1

        item = items[0]
        assert "id" in item
        assert "nombre" in item
        assert "ubigeo" in item
        assert "provincia" in item
        assert "departamento" in item

        # Check provincia structure
        assert item["provincia"]["nombre"] == "LIMA"
        assert "departamento" in item["provincia"]
        assert item["provincia"]["departamento"]["nombre"] == "LIMA"

        # Check departamento structure
        assert item["departamento"]["nombre"] == "LIMA"

    def test_get_distritos_filter_by_provincia_id(self, client: Client):
        """
        GET /api/entidades/ubigeo/distritos?provincia_id=X should filter by provincia.
        Note: IDs are UUIDs in this project, passed as strings in query params.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov_lima = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        prov_callao = UbigeoProvinciaFactory(departamento=depto, nombre="CALLAO")

        UbigeoDistritoFactory(provincia=prov_lima, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov_callao, nombre="CALLAO", ubigeo="150201")

        # Pass UUID as string since Query parameter expects UUID
        response = client.get(f"/api/entidades/ubigeo/distritos?provincia_id={prov_lima.id}")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["nombre"] == "MIRAFLORES"

    def test_get_distritos_filter_by_departamento_id(self, client: Client):
        """
        GET /api/entidades/ubigeo/distritos?departamento_id=X should filter by departamento.
        Note: IDs are UUIDs in this project, passed as strings in query params.
        """
        depto_lima = UbigeoDepartamentoFactory(nombre="LIMA")
        depto_arequipa = UbigeoDepartamentoFactory(nombre="AREQUIPA")

        prov_lima = UbigeoProvinciaFactory(departamento=depto_lima, nombre="LIMA")
        prov_arequipa = UbigeoProvinciaFactory(departamento=depto_arequipa, nombre="AREQUIPA")

        UbigeoDistritoFactory(provincia=prov_lima, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov_arequipa, nombre="AREQUIPA", ubigeo="040101")

        # Pass UUID as string since Query parameter expects UUID
        response = client.get(f"/api/entidades/ubigeo/distritos?departamento_id={depto_lima.id}")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["nombre"] == "MIRAFLORES"

    def test_get_distritos_filter_by_search(self, client: Client):
        """
        GET /api/entidades/ubigeo/distritos?search=MIRA should filter by nombre.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov, nombre="SURCO", ubigeo="150102")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRADOR", ubigeo="150103")

        response = client.get("/api/entidades/ubigeo/distritos?search=MIRA")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["data"]["total"] == 2
        nombres = {item["nombre"] for item in data["data"]["items"]}
        assert nombres == {"MIRAFLORES", "MIRADOR"}

    def test_get_distritos_returns_empty_when_no_matches(self, client: Client):
        """
        GET /api/entidades/ubigeo/distritos with non-matching filters should return empty.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")

        response = client.get("/api/entidades/ubigeo/distritos?search=NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    def test_get_distritos_combines_filters(self, client: Client):
        """
        Filters should be combinable: search + departamento_id.
        Note: IDs are UUIDs in this project.
        """
        depto_lima = UbigeoDepartamentoFactory(nombre="LIMA")
        depto_arequipa = UbigeoDepartamentoFactory(nombre="AREQUIPA")

        prov_lima = UbigeoProvinciaFactory(departamento=depto_lima, nombre="LIMA")
        prov_callao = UbigeoProvinciaFactory(departamento=depto_lima, nombre="CALLAO")
        prov_arequipa = UbigeoProvinciaFactory(departamento=depto_arequipa, nombre="AREQUIPA")

        UbigeoDistritoFactory(provincia=prov_lima, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov_callao, nombre="CALLAO", ubigeo="150201")
        UbigeoDistritoFactory(provincia=prov_arequipa, nombre="MIRADOR", ubigeo="040101")

        # Filter by departamento LIMA and search "MIRA"
        response = client.get(
            f"/api/entidades/ubigeo/distritos?departamento_id={depto_lima.id}&search=MIRA"
        )

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["nombre"] == "MIRAFLORES"
