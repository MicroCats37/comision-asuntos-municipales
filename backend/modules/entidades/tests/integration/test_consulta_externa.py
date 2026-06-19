"""
Integration tests for GET /api/entidades/consulta-sunat/{ruc} and
GET /api/entidades/consulta-reniec/{dni} endpoints.

Tests both "found" and "generated" scenarios.
"""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestConsultaSunatEndpoint:
    """Test GET /api/entidades/consulta-sunat/{ruc} endpoint."""

    def test_get_consulta_sunat_returns_200_with_hardcoded_ruc(self, client: Client):
        """
        GET /api/entidades/consulta-sunat/{ruc} should return 200 with
        institution data for a hardcoded known RUC.
        """
        response = client.get("/api/entidades/consulta-sunat/20492913151")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True

        # Verify data structure
        result = data["data"]
        assert result["ruc"] == "20492913151"
        assert result["razon_social"] == "MUNICIPALIDAD PROVINCIAL DE LIMA"
        assert result["nombre_comercial"] == "MPL"
        assert result["estado"] == "ACTIVO"
        assert result["tipo_contribuyente"] == "GOBIERNO LOCAL"
        assert result["direccion"] == "AV. PCM S/N"
        assert result["departamento"] == "LIMA"
        assert result["provincia"] == "LIMA"
        assert result["distrito"] == "LIMA"

    def test_get_consulta_sunat_returns_200_with_arbitrary_valid_ruc(self, client: Client):
        """
        GET /api/entidades/consulta-sunat/{ruc} should return 200 with
        generated institution data for any valid 11-digit RUC.
        """
        # Use a valid 11-digit RUC that is NOT in hardcoded data
        arbitrary_ruc = "10512345678"
        response = client.get(f"/api/entidades/consulta-sunat/{arbitrary_ruc}")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["ruc"] == arbitrary_ruc
        assert result["razon_social"] is not None
        assert result["nombre_comercial"] is not None
        assert result["estado"] is not None
        assert result["departamento"] is not None

    def test_get_consulta_sunat_returns_deterministic_data_for_same_ruc(self, client: Client):
        """
        GET /api/entidades/consulta-sunat/{ruc} should return the same
        generated data when called multiple times with the same RUC.
        """
        arbitrary_ruc = "10987654321"

        response1 = client.get(f"/api/entidades/consulta-sunat/{arbitrary_ruc}")
        response2 = client.get(f"/api/entidades/consulta-sunat/{arbitrary_ruc}")
        response3 = client.get(f"/api/entidades/consulta-sunat/{arbitrary_ruc}")

        data1 = response1.json()["data"]
        data2 = response2.json()["data"]
        data3 = response3.json()["data"]

        # All three calls should return identical data
        assert data1["ruc"] == data2["ruc"] == data3["ruc"] == arbitrary_ruc
        assert data1["razon_social"] == data2["razon_social"] == data3["razon_social"]
        assert data1["nombre_comercial"] == data2["nombre_comercial"] == data3["nombre_comercial"]
        assert data1["estado"] == data2["estado"] == data3["estado"]

    def test_get_consulta_sunat_validates_ruc_length(self, client: Client):
        """
        GET /api/entidades/consulta-sunat/{ruc} should return 422
        for RUC with wrong length (less than 11 digits).
        """
        # RUC too short
        response = client.get("/api/entidades/consulta-sunat/1234567890")

        assert response.status_code == 422, f"Response: {response.content}"

    def test_get_consulta_sunat_validates_ruc_max_length(self, client: Client):
        """
        GET /api/entidades/consulta-sunat/{ruc} should return 422
        for RUC with wrong length (more than 11 digits).
        """
        # RUC too long
        response = client.get("/api/entidades/consulta-sunat/123456789012")

        assert response.status_code == 422, f"Response: {response.content}"


@pytest.mark.django_db
class TestConsultaReniecEndpoint:
    """Test GET /api/entidades/consulta-reniec/{dni} endpoint."""

    def test_get_consulta_reniec_returns_200_with_hardcoded_dni(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return 200 with
        person data for a hardcoded known DNI.
        """
        response = client.get("/api/entidades/consulta-reniec/45406196")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True

        # Verify data structure
        result = data["data"]
        assert result["dni"] == "45406196"
        assert result["nombres"] == "DENNIS JOEL"
        assert result["apellidos"] == "ZARATE TORRES"
        assert result["nombre_completo"] == "ZARATE TORRES, DENNIS JOEL"
        assert result["genero"] == "M"
        assert result["fecha_nacimiento"] == "1986-08-24"

    def test_get_consulta_reniec_returns_200_with_arbitrary_valid_dni(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return 200 with
        generated person data for any valid 8-digit DNI.
        """
        # Use a valid 8-digit DNI that is NOT in hardcoded data
        arbitrary_dni = "11223344"
        response = client.get(f"/api/entidades/consulta-reniec/{arbitrary_dni}")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["dni"] == arbitrary_dni
        assert result["nombres"] is not None
        assert result["apellidos"] is not None
        assert result["nombre_completo"] is not None
        assert result["genero"] is not None
        assert result["fecha_nacimiento"] is not None

    def test_get_consulta_reniec_returns_deterministic_data_for_same_dni(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return the same
        generated data when called multiple times with the same DNI.
        """
        arbitrary_dni = "44332211"

        response1 = client.get(f"/api/entidades/consulta-reniec/{arbitrary_dni}")
        response2 = client.get(f"/api/entidades/consulta-reniec/{arbitrary_dni}")
        response3 = client.get(f"/api/entidades/consulta-reniec/{arbitrary_dni}")

        data1 = response1.json()["data"]
        data2 = response2.json()["data"]
        data3 = response3.json()["data"]

        # All three calls should return identical data
        assert data1["dni"] == data2["dni"] == data3["dni"] == arbitrary_dni
        assert data1["nombres"] == data2["nombres"] == data3["nombres"]
        assert data1["apellidos"] == data2["apellidos"] == data3["apellidos"]
        assert data1["nombre_completo"] == data2["nombre_completo"] == data3["nombre_completo"]
        assert data1["genero"] == data2["genero"] == data3["genero"]

    def test_get_consulta_reniec_validates_dni_length(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return 422
        for DNI with wrong length (less than 8 digits).
        """
        # DNI too short
        response = client.get("/api/entidades/consulta-reniec/1234567")

        assert response.status_code == 422, f"Response: {response.content}"

    def test_get_consulta_reniec_validates_dni_max_length(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return 422
        for DNI with wrong length (more than 8 digits).
        """
        # DNI too long
        response = client.get("/api/entidades/consulta-reniec/123456789")

        assert response.status_code == 422, f"Response: {response.content}"

    def test_get_consulta_reniec_returns_data_for_female_person(self, client: Client):
        """
        GET /api/entidades/consulta-reniec/{dni} should return correct
        data for female DNI.
        """
        response = client.get("/api/entidades/consulta-reniec/87654321")

        assert response.status_code == 200, f"Response: {response.content}"
        data = response.json()
        result = data["data"]
        assert result["dni"] == "87654321"
        assert result["nombres"] == "MARIA ELENA"
        assert result["apellidos"] == "LOPEZ SANCHEZ"
        assert result["genero"] == "F"
