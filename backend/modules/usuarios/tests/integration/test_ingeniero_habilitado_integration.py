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


class TestCipServiceUnavailableErrorIsHttpError:
    """Unit tests verifying CipServiceUnavailableError is a proper HttpError with 503.

    The core fix: CipServiceUnavailableError was a plain Exception (caught by
    catch-all handler → 500). It is now an HttpError subclass (caught by
    HttpError handler → 503 with proper envelope). These unit tests prove
    the exception class itself is correctly defined.

    Bug:
    - timeout: CipServiceUnavailableError: CIP API timeout for CIP 030000
    - non-200/400 response: CipServiceUnavailableError: CIP API returned 400 for CIP 999999
    These external service/search errors were returning plain 500 due to being plain Exception.

    Fix verification:
    - CipServiceUnavailableError is now an HttpError subclass with status 503
    - The HttpError exception handler returns 503 with standard error envelope
    - The catch-all Exception handler no longer catches it (so no 500)
    """

    def test_cip_service_unavailable_error_is_http_error_subclass(self):
        """
        Verify CipServiceUnavailableError is an HttpError subclass, not plain Exception.
        This is the core of the fix - the exception must be caught by the
        HttpError handler (returns proper 503) instead of the catch-all Exception
        handler (returns generic 500).
        """
        from ninja.errors import HttpError
        from core.exceptions import CipServiceUnavailableError

        assert issubclass(CipServiceUnavailableError, HttpError), (
            "CipServiceUnavailableError must be an HttpError subclass"
        )

    def test_cip_service_unavailable_error_has_503_status(self):
        """Verify the exception carries status code 503."""
        from core.exceptions import CipServiceUnavailableError

        exc = CipServiceUnavailableError("CIP API timeout")
        assert exc.status_code == 503, (
            f"Expected status 503, got {exc.status_code}"
        )

    def test_cip_service_unavailable_error_code(self):
        """Verify the exception has the correct error code CIP_SERVICE_UNAVAILABLE."""
        from core.exceptions import CipServiceUnavailableError

        exc = CipServiceUnavailableError("CIP API unavailable")
        assert exc.code == "CIP_SERVICE_UNAVAILABLE", (
            f"Expected code CIP_SERVICE_UNAVAILABLE, got {exc.code}"
        )

    def test_cip_service_unavailable_error_message(self):
        """Verify the exception carries the detail message."""
        from core.exceptions import CipServiceUnavailableError

        detail = "CIP API timeout for CIP 030000"
        exc = CipServiceUnavailableError(detail)
        # HttpError stores message as .message attribute
        assert detail in str(exc.message) or detail in str(exc)

    def test_cip_not_found_error_is_still_http_error_with_404(self):
        """
        Verify CipNotFoundError is still a separate HttpError with 404.
        This ensures the fix for service unavailable didn't affect not-found behavior.
        """
        from ninja.errors import HttpError
        from core.exceptions import CipNotFoundError

        assert issubclass(CipNotFoundError, HttpError)
        exc = CipNotFoundError(cip="999999")
        assert exc.status_code == 404
        assert exc.code == "CIP_NOT_FOUND"

    def test_service_unavailable_vs_not_found_are_separate_exceptions(self):
        """
        Verify that CipServiceUnavailableError and CipNotFoundError are distinct
        exception types with different status codes.
        """
        from core.exceptions import CipServiceUnavailableError, CipNotFoundError

        unavailable_exc = CipServiceUnavailableError("CIP API unavailable")
        not_found_exc = CipNotFoundError(cip="123456")

        assert unavailable_exc.status_code == 503
        assert not_found_exc.status_code == 404

        assert unavailable_exc.status_code != not_found_exc.status_code

        assert not isinstance(unavailable_exc, CipNotFoundError)
        assert not isinstance(not_found_exc, CipServiceUnavailableError)
