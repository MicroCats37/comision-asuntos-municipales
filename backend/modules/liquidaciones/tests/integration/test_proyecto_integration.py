"""
Integration tests for Proyectos endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

NOTE: proyectista fue removido de Proyecto — ahora vive en
LiquidacionEdificaciones.proyectistas M2M.
"""
import pytest
from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.entidad_factory import EntidadFactory
from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory


@pytest.mark.django_db
class TestCrearProyectoEndpoint:
    """Test POST /api/proyectos/ endpoint."""

    def test_post_minimal_payload_returns_200_and_public_id(self, client: Client):
        """
        POST / with only denominacion returns 200 and includes public_id.
        """
        response = client.post(
            "/api/proyectos/",
            data={"denominacion": "Mi Nuevo Proyecto"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["public_id"] is not None
        assert data["data"]["public_id"].startswith("PROY-")
        assert data["data"]["denominacion"] == "Mi Nuevo Proyecto"

    def test_post_with_entidad_id_returns_200(self, client: Client):
        """
        POST / with existing entidad_id returns 200.
        """
        entidad = EntidadFactory()

        response = client.post(
            "/api/proyectos/",
            data={
                "denominacion": "Proyecto con Entidad",
                "entidad_id": str(entidad.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["public_id"] is not None
        # entidad should be nested in response
        assert data["data"]["entidad"] is not None
        assert data["data"]["entidad"]["id"] == str(entidad.id)

    def test_post_with_distrito_id_returns_200(self, client: Client):
        """
        POST / with existing distrito_id returns 200.
        """
        distrito = UbigeoDistritoFactory()

        response = client.post(
            "/api/proyectos/",
            data={
                "denominacion": "Proyecto con Distrito",
                "distrito_id": str(distrito.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["distrito_id"] == str(distrito.id)
        assert data["data"]["distrito"] is not None

    def test_response_does_not_include_proyectista(self, client: Client):
        """
        Response should NOT include proyectista field.
        """
        response = client.post(
            "/api/proyectos/",
            data={"denominacion": "Proyecto Sin Proyectista"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        # proyectista should NOT be in response
        assert "proyectista" not in data["data"]

    def test_response_includes_entidad_when_provided(self, client: Client):
        """
        Response includes entidad nested object when entidad_id is provided.
        """
        entidad = EntidadFactory()

        response = client.post(
            "/api/proyectos/",
            data={
                "denominacion": "Proyecto Empresarial",
                "entidad_id": str(entidad.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["entidad"] is not None
        assert data["data"]["entidad"]["id"] == str(entidad.id)
        assert data["data"]["entidad"]["tipo"] == "RUC"

    def test_post_with_direccion_returns_200(self, client: Client):
        """
        POST / with direccion returns 200.
        """
        response = client.post(
            "/api/proyectos/",
            data={
                "denominacion": "Proyecto con Dirección",
                "direccion": "Av. Principal 123, Lima",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["direccion"] == "Av. Principal 123, Lima"


@pytest.mark.django_db
class TestBuscarProyectoEndpoint:
    """Test GET /api/proyectos/buscar/{public_id} endpoint."""

    def test_get_existing_project_returns_200(self, client: Client):
        """
        GET /buscar/{public_id} for existing project returns 200.
        """
        # Create a project first
        proyecto = ProyectoFactory()

        response = client.get(f"/api/proyectos/buscar/{proyecto.public_id}")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["public_id"] == proyecto.public_id
        assert data["data"]["denominacion"] == proyecto.denominacion

    def test_get_nonexistent_project_returns_200_with_null_data(self, client: Client):
        """
        GET /buscar/{public_id} for nonexistent project returns 200 with data=null.
        """
        response = client.get("/api/proyectos/buscar/PROY-INEXISTENTE-12345")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"] is None

    def test_get_response_does_not_include_proyectista(self, client: Client):
        """
        GET response should NOT include proyectista field.
        """
        proyecto = ProyectoFactory()

        response = client.get(f"/api/proyectos/buscar/{proyecto.public_id}")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "proyectista" not in data["data"]
