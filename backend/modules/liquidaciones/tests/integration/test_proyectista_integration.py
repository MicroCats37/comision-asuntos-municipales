"""
Integration tests for Proyectistas endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

NOTE: Updated to use new Proyectista contract with PerfilIngeniero and Especialidad.
Old fields (nombres, apellidos, cip, dni, cap) were replaced by perfil_ingeniero_id.
"""
import pytest
from django.test import Client

from modules.liquidaciones.tests.factories.proyectista_factory import ProyectistaFactory


@pytest.mark.django_db
class TestCrearProyectistaEndpoint:
    """Test POST /api/proyectistas/ endpoint."""

    def test_post_minimal_valid_returns_200(self, client: Client):
        """
        POST / with perfil_ingeniero_id + especialidad_id returns 200.
        descripcion is optional.
        """
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        from modules.usuarios.tests.factories.perfil_ingeniero_factory import PerfilIngenieroFactory

        perfil = PerfilIngenieroFactory()
        especialidad = EspecialidadFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "perfil_ingeniero_id": str(perfil.id),
                "especialidad_id": str(especialidad.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert data["data"]["perfil_ingeniero_id"] == str(perfil.id)
        assert data["data"]["especialidad_id"] == str(especialidad.id)
        assert data["data"]["creado"] is True
        # Optional descripcion should be None
        assert data["data"]["descripcion"] is None
        # perfil_ingeniero data should be nested
        assert data["data"]["perfil_ingeniero_nombres"] is not None
        assert data["data"]["perfil_ingeniero_apellidos"] is not None
        assert data["data"]["perfil_ingeniero_cip"] is not None

    def test_post_with_descripcion_optional_returns_200(self, client: Client):
        """
        POST / with descripcion (optional field) returns 200.
        """
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        from modules.usuarios.tests.factories.perfil_ingeniero_factory import PerfilIngenieroFactory

        perfil = PerfilIngenieroFactory()
        especialidad = EspecialidadFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "perfil_ingeniero_id": str(perfil.id),
                "especialidad_id": str(especialidad.id),
                "descripcion": "Ingeniero especialista en estructuras",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["descripcion"] == "Ingeniero especialista en estructuras"
        assert data["data"]["creado"] is True

    def test_post_missing_perfil_ingeniero_id_returns_422(self, client: Client):
        """
        POST / without required perfil_ingeniero_id returns 422.
        """
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        especialidad = EspecialidadFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "especialidad_id": str(especialidad.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_post_missing_especialidad_id_returns_422(self, client: Client):
        """
        POST / without required especialidad_id returns 422.
        """
        from modules.usuarios.tests.factories.perfil_ingeniero_factory import PerfilIngenieroFactory
        perfil = PerfilIngenieroFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "perfil_ingeniero_id": str(perfil.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_post_existing_by_perfil_ingeniero_returns_200_with_creado_false(self, client: Client):
        """
        POST / with same perfil_ingeniero+especialidad of existing proyectista
        returns 200 with creado=False.
        """
        existing = ProyectistaFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "perfil_ingeniero_id": str(existing.perfil_ingeniero_id),
                "especialidad_id": str(existing.especialidad_id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["creado"] is False
        assert data["data"]["id"] == str(existing.id)

    def test_post_response_includes_uuid_id(self, client: Client):
        """
        Response must include the created/found proyectista UUID id.
        """
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        from modules.usuarios.tests.factories.perfil_ingeniero_factory import PerfilIngenieroFactory

        perfil = PerfilIngenieroFactory()
        especialidad = EspecialidadFactory()

        response = client.post(
            "/api/proyectistas/",
            data={
                "perfil_ingeniero_id": str(perfil.id),
                "especialidad_id": str(especialidad.id),
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "id" in data["data"]
        # Should be a valid UUID string
        assert len(data["data"]["id"]) == 36