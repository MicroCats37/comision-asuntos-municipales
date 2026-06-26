"""
Integration tests for GET /api/ingenieros/habilitados/{cip} endpoint.

Tests the simplified HTTP response schema:
- cip
- nombres (nombre1 + nombre2)
- apellidos (paterno + materno)
- habilitado (bool)
- capitulo (string)

NOTE: These tests use the CipClientSimulator (active in DEBUG mode).
The controller is registered at /ingenieros directly, so the URL is /api/ingenieros/habilitados/{cip}.
"""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestIngenieroHabilitadoEndpoint:
    """Test GET /api/ingenieros/habilitados/{cip} endpoint."""

    def test_get_ingeniero_habilitado_retorna_200_con_campos_minimos(self, client: Client):
        """
        GET /habilitados/000001 debe retornar 200 con los 5 campos simplificados.

        Campos esperados en respuesta.data:
        - cip: "000001"
        - nombres: "JORGE LUIS"
        - apellidos: "GUTIERREZ TORRES"
        - habilitado: True
        - capitulo: "LIMA"
        """
        response = client.get("/api/ingenieros/habilitados/000001")
        assert response.status_code == 200, response.json()

        data = response.json()
        assert "data" in data, f"Response should have 'data' key: {data}"

        result = data["data"]

        # Verificar campos del schema simplificado
        assert "cip" in result
        assert "nombres" in result
        assert "apellidos" in result
        assert "habilitado" in result
        assert "capitulo" in result

        # Verificar que NO existen los campos del schema antiguo
        assert "paterno" not in result, "Schema antiguo no debe incluir paterno"
        assert "materno" not in result, "Schema antiguo no debe incluir materno"
        assert "nombre1" not in result, "Schema antiguo no debe incluir nombre1"
        assert "nombre2" not in result, "Schema antiguo no debe incluir nombre2"
        assert "dni" not in result, "Schema antiguo no debe incluir dni"
        assert "fechaNacimiento" not in result, "Schema antiguo no debe incluir fechaNacimiento"
        assert "capitulo" not in result or isinstance(result["capitulo"], str), \
            "capitulo debe ser string, no objeto"

    def test_get_ingeniero_habilitado_mapping_correcto_para_habilitado(self, client: Client):
        """
        Verificar mapeo correcto para CIP 000001 (habilitado=True).

        Datos del simulador:
        - cip: "000001"
        - nombre1: "JORGE", nombre2: "LUIS" → nombres: "JORGE LUIS"
        - paterno: "GUTIERREZ", materno: "TORRES" → apellidos: "GUTIERREZ TORRES"
        - condicion: "1" → habilitado: True
        - capitulo.descripcion: "LIMA" → capitulo: "LIMA"
        """
        response = client.get("/api/ingenieros/habilitados/000001")
        assert response.status_code == 200, response.json()

        result = response.json()["data"]

        assert result["cip"] == "000001"
        assert result["nombres"] == "JORGE LUIS"
        assert result["apellidos"] == "GUTIERREZ TORRES"
        assert result["habilitado"] is True
        assert result["capitulo"] == "LIMA"

    def test_get_ingeniero_habilitado_mapping_correcto_para_no_habilitado(self, client: Client):
        """
        Verificar mapeo correcto para CIP 000003 (habilitado=False).

        Datos del simulador:
        - cip: "000003"
        - nombre1: "CARLOS", nombre2: "ANTONIO" → nombres: "CARLOS ANTONIO"
        - paterno: "PEREZ", materno: "HUAMAN" → apellidos: "PEREZ HUAMAN"
        - condicion: "0" → habilitado: False
        - capitulo.descripcion: "LIMA" → capitulo: "LIMA"
        """
        response = client.get("/api/ingenieros/habilitados/000003")
        assert response.status_code == 200, response.json()

        result = response.json()["data"]

        assert result["cip"] == "000003"
        assert result["nombres"] == "CARLOS ANTONIO"
        assert result["apellidos"] == "PEREZ HUAMAN"
        assert result["habilitado"] is False
        assert result["capitulo"] == "LIMA"

    def test_get_ingeniero_habilitado_cip_inexistente_retorna_error(self, client: Client):
        """
        CIP no existente en simulador debe retornar 404 o error apropiado.
        """
        response = client.get("/api/ingenieros/habilitados/999999")
        # El endpoint puede retornar 404 o 200 con error en data
        # Verificamos que no sea 500 (error interno)
        assert response.status_code != 500, f"Should not return 500: {response.json()}"

    def test_get_ingeniero_habilitado_sin_nombre2(self, client: Client):
        """
        Verificar que el mapeo funciona cuando nombre2 es None o vacío.

        El CIP 000002 del simulador tiene nombre2: "ELENA", así que esto
        también verifica el caso completo. Si en el futuro hay datos sin
        nombre2, el presenter debe manejarlo correctamente (no agregar
        espacio extra).
        """
        response = client.get("/api/ingenieros/habilitados/000002")
        assert response.status_code == 200, response.json()

        result = response.json()["data"]

        # 000002 tiene nombre1="MARIA", nombre2="ELENA"
        assert result["nombres"] == "MARIA ELENA"
        assert result["apellidos"] == "RODRIGUEZ GOMEZ"
        assert result["habilitado"] is True


@pytest.mark.django_db
class TestIngenieroHabilitadoSchemaValidation:
    """Test que la respuesta conforms al schema IngenieroHabilitadoOut."""

    def test_responseTieneSoloCamposDefinidos(self, client: Client):
        """
        La respuesta no debe contener campos adicionales más allá de los 5 definidos.
        """
        response = client.get("/api/ingenieros/habilitados/000001")
        assert response.status_code == 200, response.json()

        result = response.json()["data"]
        expected_keys = {"cip", "nombres", "apellidos", "habilitado", "capitulo"}
        actual_keys = set(result.keys())

        extra_keys = actual_keys - expected_keys
        assert not extra_keys, f"Respuesta contiene campos extra no definidos en schema: {extra_keys}"
