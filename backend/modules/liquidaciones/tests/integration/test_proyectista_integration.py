"""
Integration tests for Proyectistas endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.
"""
import pytest
from django.test import Client

from modules.liquidaciones.tests.factories.proyectista_factory import ProyectistaFactory


@pytest.mark.django_db
class TestCrearProyectistaEndpoint:
    """Test POST /api/proyectistas/ endpoint."""

    def test_post_minimal_valid_returns_200(self, client: Client):
        """
        POST / with only nombres+apellidos returns 200 and no validation error.
        CIP/DNI are optional.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Juan",
                "apellidos": "Pérez",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["nombres"] == "Juan"
        assert data["data"]["apellidos"] == "Pérez"
        assert data["data"]["creado"] is True
        # Optional fields should be None
        assert data["data"]["cip"] is None
        assert data["data"]["dni"] is None
        assert data["data"]["cap"] is None

    def test_post_with_cip_optional_returns_200(self, client: Client):
        """
        POST / with CIP (optional field) returns 200.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "María",
                "apellidos": "García",
                "cip": "123456",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["cip"] == "123456"
        assert data["data"]["creado"] is True

    def test_post_with_dni_optional_returns_200(self, client: Client):
        """
        POST / with DNI (optional field) returns 200.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Carlos",
                "apellidos": "Rodríguez",
                "dni": "12345678",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["dni"] == "12345678"
        assert data["data"]["creado"] is True

    def test_post_with_cip_and_dni_optional_returns_200(self, client: Client):
        """
        POST / with both CIP and DNI (both optional) returns 200.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Ana",
                "apellidos": "López",
                "cip": "654321",
                "dni": "87654321",
                "cap": "111222",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["cip"] == "654321"
        assert data["data"]["dni"] == "87654321"
        assert data["data"]["cap"] == "111222"
        assert data["data"]["creado"] is True

    def test_post_missing_nombres_returns_422(self, client: Client):
        """
        POST / without required nombres returns 422.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "apellidos": "Sin Nombre",
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_post_missing_apellidos_returns_422(self, client: Client):
        """
        POST / without required apellidos returns 422.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Sin Apellido",
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_post_existing_by_dni_returns_200_with_creado_false(self, client: Client):
        """
        POST / with DNI of existing proyectista returns 200 with creado=False.
        """
        existing = ProyectistaFactory(dni="11223344", nombres="Existente", apellidos="Proyectista")

        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Otro Nombre",
                "apellidos": "Otra Apellido",
                "dni": "11223344",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["creado"] is False
        assert data["data"]["id"] == str(existing.id)
        assert data["data"]["dni"] == "11223344"

    def test_post_response_includes_uuid_id(self, client: Client):
        """
        Response must include the created/found proyectista UUID id.
        """
        response = client.post(
            "/api/proyectistas/",
            data={
                "nombres": "Test",
                "apellidos": "UUID",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "id" in data["data"]
        # Should be a valid UUID string
        assert len(data["data"]["id"]) == 36